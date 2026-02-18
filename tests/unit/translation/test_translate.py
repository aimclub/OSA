def test_translate_text_excluded(translator):
    # Assert
    assert translator._translate_text("README") == "README"


def test_translate_text(translator):
    """
    Test that the translator's private `_translate_text` method correctly returns the
    translated text provided by the mocked `model_handler`.
    
    Parameters
    ----------
    translator
        The translator instance whose `_translate_text` method is being tested. The
        method is expected to have a `model_handler` attribute with a
        `send_request` method that can be mocked.
    
    Returns
    -------
    None
        This function performs an assertion and does not return a value.
    """
    # Arrange
    translator.model_handler.send_request.return_value = "translated_text"
    # Assert
    assert translator._translate_text("тест") == "translated_text"
