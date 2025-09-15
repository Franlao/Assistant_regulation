import pytest
from unittest.mock import Mock, patch, mock_open
import streamlit as st

@pytest.fixture
def mock_streamlit():
    with patch.multiple('streamlit',
                       session_state=Mock(),
                       sidebar=Mock(),
                       write=Mock(),
                       markdown=Mock(),
                       selectbox=Mock(),
                       slider=Mock(),
                       checkbox=Mock()) as mocks:
        yield mocks

class TestUIComponents:
    
    def test_load_all_styles(self):
        from assistant_regulation.app.ui_styles import load_all_styles
        # Test that function runs without error
        try:
            load_all_styles()
        except Exception as e:
            pytest.fail(f"load_all_styles raised {e}")
    
    def test_add_bg_from_local(self, mocker):
        from assistant_regulation.app.ui_styles import add_bg_from_local
        
        # Utiliser pytest-mock au lieu des decorators @patch
        mock_st = mocker.patch('assistant_regulation.app.ui_styles.st')
        mocker.patch('builtins.open', mocker.mock_open(read_data=b'fake image data'))
        mocker.patch('base64.b64encode', return_value=b'ZmFrZSBpbWFnZSBkYXRh')
        
        add_bg_from_local("test_image.jpg")
        mock_st.markdown.assert_called()

class TestTranslations:
    
    def test_get_text_fr(self):
        from translations import get_text
        text = get_text("app_title", "fr")
        assert isinstance(text, str)
        assert len(text) > 0
    
    def test_get_text_en(self):
        from translations import get_text
        text = get_text("app_title", "en")
        assert isinstance(text, str)
        assert len(text) > 0
    
    def test_get_text_fallback(self):
        from translations import get_text
        text = get_text("nonexistent_key", "fr")
        assert text == "nonexistent_key"