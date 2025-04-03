def test_translate_text_excluded(translator):
    # Assert
    assert translator._translate_text("README") == "README"


def test_translate_text(translator):
    # Arrange
    translator.model_handler.send_request.return_value = "translated_text"
    # Assert
    assert translator._translate_text("тест") == "translated_text"
