from v2s.translate import parse_marked_lines


def test_parse_marked_lines():
    content = "1|Bonjour\n2|Comment vas-tu?\n3: Au revoir"
    parsed = parse_marked_lines(content)
    assert parsed == {
        1: "Bonjour",
        2: "Comment vas-tu?",
        3: "Au revoir",
    }


def test_parse_marked_lines_ignores_notes():
    content = "Here are the translations:\n1|Bonjour\nNote: done"
    assert parse_marked_lines(content) == {1: "Bonjour"}

