import difflib
import html


def render_diff_html(original: str, revised: str) -> str:
    """Word-level diff between two texts, rendered as highlighted HTML spans."""
    original_words = original.split()
    revised_words = revised.split()
    matcher = difflib.SequenceMatcher(a=original_words, b=revised_words)

    parts: list[str] = []
    for tag, a_start, a_end, b_start, b_end in matcher.get_opcodes():
        if tag == "equal":
            text = html.escape(" ".join(original_words[a_start:a_end]))
            parts.append(text)
        elif tag == "delete":
            text = html.escape(" ".join(original_words[a_start:a_end]))
            parts.append(f'<span style="background-color:#4a1f1f;color:#ff8080;text-decoration:line-through;">{text}</span>')
        elif tag == "insert":
            text = html.escape(" ".join(revised_words[b_start:b_end]))
            parts.append(f'<span style="background-color:#1f3a1f;color:#7dff7d;">{text}</span>')
        elif tag == "replace":
            old_text = html.escape(" ".join(original_words[a_start:a_end]))
            new_text = html.escape(" ".join(revised_words[b_start:b_end]))
            parts.append(f'<span style="background-color:#4a1f1f;color:#ff8080;text-decoration:line-through;">{old_text}</span>')
            parts.append(f'<span style="background-color:#1f3a1f;color:#7dff7d;">{new_text}</span>')

    return " ".join(parts)
