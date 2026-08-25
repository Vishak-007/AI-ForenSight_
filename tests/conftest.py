"""
Shared pytest fixtures for the translation pipeline tests.

Model-dependent tests (real NLLB/grammar-correction inference) are marked
@pytest.mark.model and skipped automatically if the required libraries or
models aren't available/downloadable - this keeps the fast unit tests
(lang_id, transliterate lexicon logic, tokenizer, reconstruct) runnable
offline without torch/transformers installed.
"""

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "model: requires real NLLB/grammar-correction inference")


@pytest.fixture(scope="session")
def models_available():
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError:
        return False

    try:
        from translation import nllb_translate
        nllb_translate._get_model_and_tokenizer()
    except Exception:
        return False

    return True


@pytest.fixture(autouse=True)
def _skip_model_tests_if_unavailable(request, models_available):
    if request.node.get_closest_marker("model") and not models_available:
        pytest.skip("NLLB/transformers/torch not available in this environment")
