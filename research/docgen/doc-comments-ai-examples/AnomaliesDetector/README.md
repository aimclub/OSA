# Here are the notes of the [doc-comments-ai utility](https://github.com/fynnfluegge/doc-comments-ai) work results respectively to the [ITMO-NSS-team AnomaliesDetector repository](https://github.com/ITMO-NSS-team/AnomaliesDetector)

- It is a bit troublesome to run at the first place due to the fact doc-comments-ai's log responses contain a visual redundants such as emojis which causes a specific encoding conflicts with some terminals i.e. git-bash and doesn't let run the core features of the tool. Therefore it is crucial to dig in the source files and fix the respective outputs
- For the same reasons the 'yaspin' module (generates a loading animation) errors are thrown highly in numbers to the terminal which makes it litterated and hard to read. Nevertheless it doesn't affect vital features of the tool and in result it lists modules the comments were generated for
- In data.py and several other modules the utility leaves the 'bad batch' comments before the corresponding methods and functions uncleared
- A wide span problem with Python methods' indentations - the utility breaks the correct implementation of Python's indentaions at the OOP methodes
- At the 531 line (ice_model.py) of the "ocean_with_mlp" method a closing ']' has vanished
- Clears out '#' comments in the code

## Overall experience

- There are a lot of things that are supposed to be taken care of thoroughly 'by hands' after comments generation (indentations, syntax errors and etc) which is kinda downfall
- The generated comments might be useful for the 'formal' and general description of the application's methods but they lack on specifics
- The final documentation image is yet to be done by Sphinx or some other way to stitch doc-comments together 
