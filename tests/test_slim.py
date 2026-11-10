"""Unit tests for code slimming."""

from tg.slim import slim_python, slim_c_like


def test_slim_python():
    code = '''
# Top level comment
def add(a, b):
    """Add two numbers together."""
    # Internal comment
    return a + b
'''
    slimmed = slim_python(code)
    assert "# Top level comment" not in slimmed
    assert "# Internal comment" not in slimmed
    assert "Add two numbers together" not in slimmed
    assert "def add(a, b):" in slimmed
    assert "return a + b" in slimmed


def test_slim_c_like():
    code = """
// File header comment
/* Multi-line
   comment */
function greet(name) {
    // return greeting
    return "Hello " + name;
}
"""
    slimmed = slim_c_like(code)
    assert "// File header comment" not in slimmed
    assert "Multi-line" not in slimmed
    assert "// return greeting" not in slimmed
    assert 'return "Hello " + name;' in slimmed

