import os
import math
import cv2
import json
import base64

from doclayout_yolo import YOLOv10
from huggingface_hub import hf_hub_download
import numpy as np
from tqdm import tqdm

import torch

from osa_tool.utils.logger import logger

from osa_tool.operations.analysis.repository_validation.paper_parsing import doc_geometry, paper_utils
from osa_tool.operations.analysis.repository_validation.paper_parsing.graph_utils import element_node_id


class LayoutExtractor:
    def __init__(
        self,
        device: str = "cuda",
        save_img: bool = False,
        model_name: str = "juliozhao/DocLayout-YOLO-DocStructBench",
        weights_name: str = "doclayout_yolo_docstructbench_imgsz1024.pt",
    ) -> None:
        """Class for bbox extraction and document parts processing

        Args:
            device (str, optional): device type "cpu"/"cuda". Defaults to "cuda".
            save_img (bool, optional): an argument to define save processed images or not. Defaults to False.
            model_name (str, optional): model name. Defaults to "juliozhao/DocLayout-YOLO-DocStructBench".
            weights_name (str, optional): weights name. Defaults to "doclayout_yolo_docstructbench_imgsz1024.pt".
        """
        # Load the pre-trained model
        model_path = hf_hub_download(repo_id=model_name, filename=weights_name)
        self.device = device
        self.save_img = save_img

        self.model = YOLOv10(model_path).to(device)

        self.labels = {
            0: "title",
            1: "plain text",
            2: "abandon",
            3: "figure",
            4: "figure_caption",
            5: "table",
            6: "table_caption",
            7: "table_footnote",
            8: "isolate_formula",
            9: "formula_caption",
        }

        self.label_mapping = {
            "figure_caption": "figure",
            "table_caption": "table",
            "table_footnote": "table",
            "formula_caption": "isolate_formula",
        }

        self.doc_path = None

        # Parts concatenation related
        self.captions = []
        self.specific_elems = []
        self.relevant_pairs = []

    def get_bboxes(
        self,
        doc_path: str,
        output_path: str = None,
        # img_size: int = 1024,
        conf_threshold: float = 0.15,
        concatenate: bool = True,
    ) -> list:
        """The main method to call the YOLO model and extract bboxes.
        It provides self.pages, which collects arrays for every page
        as an image in the case of a PDF document. It  returns bboxes
        represented in JSON-like format.

        Args:
            doc_path (str): path to the document to process, it can be image, or pdf.
            output_path (str, optional): path to the file to save returned result. Defaults to None.
            conf_threshold (float, optional): minimum confidence level of YOLO model. Defaults to 0.15.

        Returns:
            bbox_json: [{'name': str,
                        'class': int,
                        'confidence': float,
                        'box': {'x1': float,
                        'y1': float,
                        'x2': float,
                        'y2': float}]
        """
        self.doc_path = doc_path

        self.pages = []
        self.bboxes = []

        if ".pdf" in self.doc_path:
            self.pages = paper_utils.process_pdf(self.doc_path)
            self.bboxes = self.model.predict(self.pages, conf=conf_threshold, device=self.device)
        else:
            bbox_result = self.model.predict(doc_path, conf=conf_threshold, device=self.device)
            self.bboxes = bbox_result if isinstance(bbox_result, list) else [bbox_result]

        return self._process_bbox_results(output_path, concatenate=concatenate)

    def get_bboxes_batched(
        self,
        doc_path: str,
        output_path: str = None,
        conf_threshold: float = 0.15,
        batch_size: int = 5,
        max_pages: int = None,
        concatenate: bool = True,
    ) -> list:
        """Process large documents in batches to manage CUDA memory"""

        self.doc_path = doc_path
        self.pages = []
        self.bboxes = []

        if ".pdf" in self.doc_path:
            self.pages = paper_utils.process_pdf(self.doc_path)

            if max_pages:
                self.pages = self.pages[:max_pages]

            for i in tqdm(range(0, len(self.pages), batch_size)):
                batch_pages = self.pages[i : i + batch_size]

                batch_bboxes = self.model.predict(batch_pages, conf=conf_threshold, device=self.device, verbose=False)
                self.bboxes.extend(batch_bboxes)

                if self.device == "cuda":
                    torch.cuda.empty_cache()
        else:
            # Single image processing
            bbox_result = self.model.predict(doc_path, conf=conf_threshold, device=self.device)
            self.bboxes = bbox_result if isinstance(bbox_result, list) else [bbox_result]

        return self._process_bbox_results(output_path, concatenate=concatenate)

    def _process_bbox_results(self, output_path: str = None, concatenate: bool = True) -> list:
        """Process bbox results after prediction (shared logic for both methods)"""

        if self.save_img:
            # Annotate and save the result
            for i in range(len(self.bboxes)):
                annotated_frame = self.bboxes[i].plot(pil=True, line_width=5, font_size=20)
                annot_name = os.path.basename(self.doc_path).split(".")
                annot_name = annot_name[0] + "_layout" + "_" + str(i) + ".jpg"
                if output_path:
                    cv2.imwrite(
                        os.path.join(os.path.dirname(output_path), annot_name),
                        annotated_frame,
                    )

        self.bbox_json = []
        for i in tqdm(range(len(self.bboxes))):
            current_bbox_json = json.loads(self.bboxes[i].tojson())
            current_bbox_json = self.merge_duplicated(bbox_json=current_bbox_json, iou_threshold=0.75)
            for j in range(len(current_bbox_json)):
                current_bbox_json[j]["page_num"] = i

            self.bbox_json.extend(current_bbox_json)

        for i in range(len(self.bbox_json)):
            self.bbox_json[i]["centroid"] = self._get_centoid(bbox_idx=i)
            # image_bytes is encoded here, before parts concatenation: the merge
            # steps in _concatenate_parts() consume these per-element crops, so
            # the encoding cannot be deferred past them.
            self.bbox_json[i]["image_bytes"] = self.encode_image(bbox_idx=i)
            self.bbox_json[i]["bbox_idx"] = i

            # specific symbols from the pages, not supposed to be analyzed
            if self.bbox_json[i]["name"] == "abandon":
                self.bbox_json[i]["ignore"] = True
            else:
                self.bbox_json[i]["ignore"] = False

        if concatenate:
            self._concatenate_parts()

        if output_path:
            for i in range(len(self.bbox_json)):
                self.bbox_json[i]["image_bytes"] = str(self.bbox_json[i]["image_bytes"])

            with open(output_path, "w") as f:
                json.dump(self.bbox_json, f, ensure_ascii=False, indent=2)

        return self.bbox_json

    def _concatenate_parts(self) -> list:
        """Merge related layout parts detected across the pages.

        Runs, in order:
          1. caption/figure(table) pairing and vertical concatenation of their
             crops (:meth:`_find_closest_bboxes` + :meth:`_merge_related_bboxes`),
          2. merging of vertically adjacent paragraphs / titles
             (:meth:`_merge_adjacent_plain_texts`),
          3. attaching captions that sit around figures / tables / formulas
             (:meth:`_detect_captions_around_figures`).

        Must run after per-element ``image_bytes`` have been encoded, since the
        merge steps concatenate those crops. Mutates and returns ``bbox_json``.

        Finishes with :meth:`_reindex_elements`, which restores the invariant
        that ``bbox_json[i]["bbox_idx"] == i`` after the merge steps have dropped
        entries, and stamps each element with the ``node_id`` the graph builder
        will use.
        """
        self._find_closest_bboxes()
        self._merge_related_bboxes()
        self._merge_adjacent_plain_texts(distance_ratio=0.25, abs_gap_px=18)
        self._detect_captions_around_figures(distance_ratio=0.1)
        self._reindex_elements()
        return self.bbox_json

    def _reindex_elements(self) -> None:
        """Renumber elements so list position, ``bbox_idx`` and ``node_id`` agree.

        ``bbox_idx`` is assigned before merging, but ``_merge_adjacent_plain_texts``
        removes absorbed entries, so afterwards the stored index no longer matches
        the element's position — leaving graph node ids that cannot be resolved
        back to a report entry. Here the original detection index is preserved as
        ``source_idx`` (for tracing back to the raw YOLO output) while ``bbox_idx``
        becomes the position again.

        Caption links recorded during merging refer to pre-merge ``bbox_idx``
        values, so they are remapped to the new numbering in the same pass.
        """
        remap = {elem["bbox_idx"]: position for position, elem in enumerate(self.bbox_json)}

        for position, elem in enumerate(self.bbox_json):
            elem["source_idx"] = elem["bbox_idx"]
            elem["bbox_idx"] = position
            elem["node_id"] = element_node_id(position)

        for elem in self.bbox_json:
            if elem.get("caption_for") is not None:
                elem["caption_for"] = remap.get(elem["caption_for"])
            if elem.get("captions"):
                elem["captions"] = [remap[i] for i in elem["captions"] if i in remap]

    # TODO: drop it to utils to avoid rewriting it in doc_ocr
    def encode_image(self, bbox_idx):
        _bbox = self.bbox_json[bbox_idx]["box"]
        x1, y1, x2, y2 = [i for i in _bbox.values()]

        x = math.floor(x1)
        y = math.floor(y1)
        w = math.ceil(x2) - x
        h = math.ceil(y2) - y

        if ".pdf" in self.doc_path:
            image = self.pages[self.bbox_json[bbox_idx]["page_num"]]

        else:
            image = cv2.imread(self.doc_path)

        cropped_img = image[y : y + h, x : x + w]
        retval, buffer = cv2.imencode(".jpg", cropped_img)
        jpg_as_bytes = base64.b64encode(buffer)
        return jpg_as_bytes

    def merge_duplicated(self, bbox_json, iou_threshold: float = 0.75) -> list:
        """Method to merge overlaped bboxes. It considers the Intersection over Union (iou)
        and save a bbox with the higher confidence level.

        Args:
            bbox_json (list): result of get_bboxes
            iou_threshold (float, optional): Intersection over Union level. Defaults to 0.75.

        Returns:
            bbox_json: [{'name': str,
                        'class': int,
                        'confidence': float,
                        'box': {'x1': float,
                        'y1': float,
                        'x2': float,
                        'y2': float}]
        """
        name_groups = {}
        for box in bbox_json:
            name = box["name"]
            if name not in name_groups:
                name_groups[name] = []
            name_groups[name].append(box)

        merged_boxes = []

        for name, group in name_groups.items():
            group.sort(key=lambda x: -x["confidence"])
            i = 0
            while i < len(group):
                current = group[i]
                j = i + 1
                while j < len(group):
                    candidate = group[j]
                    iou = self._calculate_iou(current["box"], candidate["box"])
                    if iou > iou_threshold:
                        current = self._merge_two_boxes(current, candidate)
                        group.pop(j)
                    else:
                        j += 1
                merged_boxes.append(current)
                i += 1

        bbox_json = merged_boxes
        return bbox_json

    def _calculate_iou(self, bbox1, bbox2):
        # Determine coordinates of intersection rectangle
        x_left = max(bbox1["x1"], bbox2["x1"])
        y_top = max(bbox1["y1"], bbox2["y1"])
        x_right = min(bbox1["x2"], bbox2["x2"])
        y_bottom = min(bbox1["y2"], bbox2["y2"])

        if x_right < x_left or y_bottom < y_top:
            return 0.0

        intersection_area = (x_right - x_left) * (y_bottom - y_top)

        bbox1_area = (bbox1["x2"] - bbox1["x1"]) * (bbox1["y2"] - bbox1["y1"])
        bbox2_area = (bbox2["x2"] - bbox2["x1"]) * (bbox2["y2"] - bbox2["y1"])

        union_area = bbox1_area + bbox2_area - intersection_area

        iou = intersection_area / union_area
        return iou

    def _merge_two_boxes(self, bbox1, bbox2) -> list:
        # Keep box with higher confidence
        merged = bbox1 if bbox1["confidence"] >= bbox2["confidence"] else bbox2

        merged_box_coords = {
            "x1": min(bbox1["box"]["x1"], bbox2["box"]["x1"]),
            "y1": min(bbox1["box"]["y1"], bbox2["box"]["y1"]),
            "x2": max(bbox1["box"]["x2"], bbox2["box"]["x2"]),
            "y2": max(bbox1["box"]["y2"], bbox2["box"]["y2"]),
        }

        merged["confidence"] = max(bbox1["confidence"], bbox2["confidence"])
        merged["box"] = merged_box_coords

        return merged

    def _get_centoid(self, bbox_idx):
        bbox_coors = self.bbox_json[bbox_idx]["box"]
        return (
            (bbox_coors["x1"] + bbox_coors["x2"]) / 2,
            (bbox_coors["y1"] + bbox_coors["y2"]) / 2,
        )

    def _find_closest_bboxes(self):
        """Find related bboxes based on label_mapping and cosine similarity
        of centroids.
        """
        for i in range(len(self.bbox_json)):
            if self.bbox_json[i]["name"] in self.label_mapping:
                self.captions.append(self.bbox_json[i])
                self.bbox_json[i]["ignore"] = True  # because it'll be concatenated
            elif self.bbox_json[i]["name"] in self.label_mapping.values():
                self.specific_elems.append(self.bbox_json[i])

        for caption_id, caption in enumerate(self.captions):
            max_similarity = -1
            closest_elem_id = None

            for elem_id, elem in enumerate(self.specific_elems):
                if elem["name"] != self.label_mapping[caption["name"]]:
                    continue

                if elem["page_num"] != caption["page_num"]:
                    continue

                similarity = paper_utils.cosine_similarity(caption["centroid"], elem["centroid"])

                if similarity > max_similarity:
                    max_similarity = similarity
                    closest_elem_id = elem_id

            if closest_elem_id is not None:
                self.relevant_pairs.append(
                    {
                        "caption_id": caption_id,
                        "element_id": closest_elem_id,
                        "similarity": max_similarity,
                    }
                )
                self._record_caption_link(caption, self.specific_elems[closest_elem_id])

    @staticmethod
    def _record_caption_link(caption: dict, element: dict) -> None:
        """Record that *caption* belongs to *element*.

        The caption's pixels end up inside the element's crop, so the VLM only
        ever describes the pair as a unit and the caption element itself stays
        empty. Persisting the pairing here lets the graph builder emit a
        ``caption_of`` edge from what structural parsing actually decided,
        instead of re-guessing it by centroid distance over textless nodes.

        Indices are stored as pre-merge ``bbox_idx`` values and rewritten by
        :meth:`_reindex_elements` once positions are final.
        """
        caption["caption_for"] = element["bbox_idx"]
        element.setdefault("captions", []).append(caption["bbox_idx"])

    def _merge_related_bboxes(self):
        """Method to merge related pairs of bboxes, which are found with _find_closest_bboxes."""
        for pair in self.relevant_pairs:
            caption_id = pair["caption_id"]
            element_id = pair["element_id"]

            try:
                part1 = paper_utils.readb64(eval(self.captions[caption_id]["image_bytes"]))
            except SyntaxError:
                part1 = paper_utils.readb64(self.captions[caption_id]["image_bytes"])
            try:
                part2 = paper_utils.readb64(eval(self.specific_elems[element_id]["image_bytes"]))
            except SyntaxError:
                part2 = paper_utils.readb64(self.specific_elems[element_id]["image_bytes"])

            height1, width1 = part1.shape[:2]
            height2, width2 = part2.shape[:2]

            if width1 != width2:
                if width1 < width2:
                    new_height = int(height1 * (width2 / width1))
                    part1 = cv2.resize(part1, (width2, new_height))
                else:
                    new_height = int(height2 * (width1 / width2))
                    part2 = cv2.resize(part2, (width1, new_height))

            merged_parts = cv2.vconcat([part1, part2])

            # rewrite the specific element with merged
            changed_id = self.specific_elems[element_id]["bbox_idx"]
            self.bbox_json[changed_id]["image_bytes"] = paper_utils.encode_bbox(merged_parts)

    def _merge_adjacent_plain_texts(self, bboxes: list = None, distance_ratio: float = 0.18, abs_gap_px: int = 18):
        """Merge vertically adjacent text fragments of the *same* kind.

        Detection often splits one paragraph across several boxes; stitching them
        back together gives the VLM a coherent fragment. Merging is restricted to
        elements sharing a name, so a ``title`` never absorbs the body text under
        it — that would erase the section boundary the graph relies on and, on a
        title page, collapse the whole page into a single heading.
        """

        if bboxes is None:
            bboxes = self.bbox_json

        def overlap_ratio_x(b1, b2):
            x_left = max(b1["x1"], b2["x1"])
            x_right = min(b1["x2"], b2["x2"])
            if x_right <= x_left:
                return 0.0
            inter = x_right - x_left
            w_min = min(max(1.0, b1["x2"] - b1["x1"]), max(1.0, b2["x2"] - b2["x1"]))
            return inter / (w_min + 1e-9)

        candidates = [
            (i, bb)
            for i, bb in enumerate(self.bbox_json)
            if (not bb.get("ignore", False)) and bb.get("name") in ("plain text", "title")
        ]

        if not candidates:
            return

        candidates.sort(key=lambda t: (t[1].get("page_num", 0), *doc_geometry.reading_order_key(t[1])))
        idxs = [c[0] for c in candidates]
        removed = set()
        i = 0
        n = len(idxs)

        def decode_img(entry):
            raw = entry.get("image_bytes", None)
            if raw is None:
                return None
            try:
                if isinstance(raw, (bytes, bytearray, memoryview)):
                    return paper_utils.readb64(raw)
            except Exception:
                pass
            if isinstance(raw, str):
                try:
                    if (raw.startswith("b'") and raw.endswith("'")) or (raw.startswith('b"') and raw.endswith('"')):
                        evaluated = eval(raw)
                        return paper_utils.readb64(evaluated)
                except Exception:
                    pass
                try:
                    data = base64.b64decode(raw)
                    arr = np.frombuffer(data, dtype=np.uint8)
                    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    return img
                except Exception:
                    pass
            try:
                return paper_utils.readb64(raw)
            except Exception:
                return None

        while i < n:
            idx_i = idxs[i]
            if idx_i in removed:
                i += 1
                continue

            primary_box = dict(self.bbox_json[idx_i]["box"])
            page = self.bbox_json[idx_i].get("page_num", 0)
            kind = self.bbox_json[idx_i].get("name")
            cluster = [idx_i]

            j = i + 1
            while j < n:
                idx_j = idxs[j]
                if idx_j in removed:
                    j += 1
                    continue
                if self.bbox_json[idx_j].get("page_num", 0) != page:
                    break
                if self.bbox_json[idx_j].get("name") != kind:
                    j += 1
                    continue

                box_j = self.bbox_json[idx_j]["box"]
                if box_j["y1"] >= primary_box["y2"]:
                    vgap = box_j["y1"] - primary_box["y2"]
                elif primary_box["y1"] >= box_j["y2"]:
                    vgap = primary_box["y1"] - box_j["y2"]
                else:
                    vgap = -min(primary_box["y2"] - box_j["y1"], box_j["y2"] - primary_box["y1"])

                min_h = min(
                    max(1.0, primary_box["y2"] - primary_box["y1"]),
                    max(1.0, box_j["y2"] - box_j["y1"]),
                )
                hx = overlap_ratio_x(primary_box, box_j)

                cond_gap = vgap <= max(min_h * distance_ratio, abs_gap_px)
                cond_hx = hx >= 0.35

                if cond_gap and cond_hx:
                    primary_box = {
                        "x1": min(primary_box["x1"], box_j["x1"]),
                        "y1": min(primary_box["y1"], box_j["y1"]),
                        "x2": max(primary_box["x2"], box_j["x2"]),
                        "y2": max(primary_box["y2"], box_j["y2"]),
                    }
                    cluster.append(idx_j)
                    removed.add(idx_j)
                j += 1

            if len(cluster) > 1:
                primary_idx = cluster[0]
                merged_coords = primary_box

                mw = int(max(1, merged_coords["x2"] - merged_coords["x1"]))
                mh = int(max(1, merged_coords["y2"] - merged_coords["y1"]))
                canvas = np.ones((mh, mw, 3), dtype=np.uint8) * 255
                any_pasted = False

                for cid in cluster:
                    entry = self.bbox_json[cid]
                    if entry.get("name") not in ("plain text", "title"):
                        continue
                    box = entry["box"]
                    dx = int(box["x1"] - merged_coords["x1"])
                    dy = int(box["y1"] - merged_coords["y1"])
                    img = decode_img(entry)
                    if img is None:
                        continue
                    ih, iw = img.shape[:2]
                    paste_w = min(iw, mw - dx)
                    paste_h = min(ih, mh - dy)
                    if paste_w > 0 and paste_h > 0:
                        canvas[dy : dy + paste_h, dx : dx + paste_w] = img[0:paste_h, 0:paste_w]
                        any_pasted = True

                if any_pasted:
                    try:
                        self.bbox_json[primary_idx]["image_bytes"] = paper_utils.encode_bbox(canvas)
                    except Exception:
                        pass

                self.bbox_json[primary_idx]["box"] = merged_coords
                self.bbox_json[primary_idx]["centroid"] = (
                    (merged_coords["x1"] + merged_coords["x2"]) / 2.0,
                    (merged_coords["y1"] + merged_coords["y2"]) / 2.0,
                )
                self.bbox_json[primary_idx]["absorbed_source_idx"] = [
                    self.bbox_json[cid]["bbox_idx"] for cid in cluster[1:]
                ]

            # Advance one element at a time so every element can seed its own
            # cluster; already-absorbed ones are skipped via ``removed`` at the
            # top of the loop. Jumping to ``j`` here would skip to the next page
            # and leave at most one merged cluster per page.
            i += 1

        if not removed:
            return

        self.bbox_json = [entry for k, entry in enumerate(self.bbox_json) if k not in removed]
        logger.debug(f"_merge_adjacent_plain_texts: removed {len(removed)}, total {len(self.bbox_json)}")

    def _detect_captions_around_figures(
        self,
        bboxes: list = None,
        distance_ratio: float = 0.1,
        caption_height_ratio: float = 0.5,
    ):
        """Attach captions sitting around a figure / table / formula to it.

        The element's box grows to cover its captions and its crop is re-cut from
        the page so the VLM sees the pair as a unit; the caption elements are
        then marked ``ignore`` and linked back with :meth:`_record_caption_link`.

        Args:
            distance_ratio: How far around the element to look for captions, as a
                fraction of its longest side.
            caption_height_ratio: A ``plain text`` / ``title`` neighbour is only
                reclassified as a caption when it is no taller than this fraction
                of the element. Without the guard, a formula sitting next to a
                column of body text absorbs the whole column and that text is
                dropped from the document. Neighbours the detector already
                classified as captions are attached regardless of size.
        """
        if bboxes is None:
            bboxes = self.bbox_json

        caption_for = {
            "figure": "figure_caption",
            "table": "table_caption",
            "isolate_formula": "formula_caption",
        }
        elements = [
            (i, b) for i, b in enumerate(bboxes) if (not b.get("ignore", False)) and b["name"] in caption_for.keys()
        ]
        caption_candidates = [
            (i, b)
            for i, b in enumerate(bboxes)
            if (not b.get("ignore", False))
            and b["name"]
            in (
                "plain text",
                "title",
                "figure_caption",
                "table_caption",
                "formula_caption",
            )
        ]

        def try_get_page_image(page_num):
            """Raster the element's box was measured against.

            Same source :meth:`encode_image` crops from, so the widened box and
            the re-cut crop stay in register. This used to look for
            ``page_images`` / ``page_rasters``, which the class never sets, so it
            always returned ``None`` and the crop was never actually widened —
            the absorbed caption was dropped from the text *and* missing from
            the image the VLM saw.
            """
            if ".pdf" in self.doc_path:
                return self.pages[page_num] if page_num < len(self.pages) else None
            return cv2.imread(self.doc_path)

        for elem_idx, elem in elements:
            page = elem.get("page_num", 0)
            elem_box = elem["box"]
            w = elem_box["x2"] - elem_box["x1"]
            h = elem_box["y2"] - elem_box["y1"]
            expand = max(w, h) * distance_ratio
            exp = {
                "x1": elem_box["x1"] - expand,
                "y1": elem_box["y1"] - expand,
                "x2": elem_box["x2"] + expand,
                "y2": elem_box["y2"] + expand,
            }

            nearby = []
            for cand_idx, cand in caption_candidates:
                if cand_idx == elem_idx or cand.get("page_num", 0) != page:
                    continue
                c = cand["box"]
                if c["x2"] < exp["x1"] or c["x1"] > exp["x2"] or c["y2"] < exp["y1"] or c["y1"] > exp["y2"]:
                    continue
                # Body text merely adjacent to a formula is not its caption; only
                # a short strip qualifies for reclassification.
                if cand["name"] in ("plain text", "title") and (c["y2"] - c["y1"]) > caption_height_ratio * h:
                    continue
                nearby.append((cand_idx, cand))

            if not nearby:
                continue

            all_x1 = [elem_box["x1"]] + [c[1]["box"]["x1"] for c in nearby]
            all_y1 = [elem_box["y1"]] + [c[1]["box"]["y1"] for c in nearby]
            all_x2 = [elem_box["x2"]] + [c[1]["box"]["x2"] for c in nearby]
            all_y2 = [elem_box["y2"]] + [c[1]["box"]["y2"] for c in nearby]
            merged_coords = {
                "x1": min(all_x1),
                "y1": min(all_y1),
                "x2": max(all_x2),
                "y2": max(all_y2),
            }

            page_img = try_get_page_image(page)
            if page_img is not None and isinstance(page_img, (np.ndarray,)):
                h_img, w_img = page_img.shape[:2]
                mx1 = int(max(0, merged_coords["x1"]))
                my1 = int(max(0, merged_coords["y1"]))
                mx2 = int(min(w_img, merged_coords["x2"]))
                my2 = int(min(h_img, merged_coords["y2"]))
                if mx2 > mx1 and my2 > my1:
                    crop = page_img[my1:my2, mx1:mx2].copy()
                    try:
                        self.bbox_json[elem_idx]["image_bytes"] = paper_utils.encode_bbox(crop)
                    except Exception:
                        pass

            self.bbox_json[elem_idx]["box"] = merged_coords
            self.bbox_json[elem_idx]["centroid"] = (
                (merged_coords["x1"] + merged_coords["x2"]) / 2,
                (merged_coords["y1"] + merged_coords["y2"]) / 2,
            )

            for cand_idx, _ in nearby:
                if cand_idx != elem_idx:
                    # rename if needed
                    if self.bbox_json[cand_idx]["name"] in ("plain text", "title"):
                        self.bbox_json[cand_idx]["name"] = caption_for.get(elem["name"], "figure_caption")
                    self.bbox_json[cand_idx]["ignore"] = True
                    self._record_caption_link(self.bbox_json[cand_idx], self.bbox_json[elem_idx])
