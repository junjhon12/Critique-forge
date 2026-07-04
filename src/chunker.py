def user_text(text:str, max_words: int = 10000) -> list[str]:
    if not text.strip():
        return []
    
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_word_count = 0
    
    for paragraph in paragraphs:
        paragraph_word_count = len(paragraph.split())
        
        if current_word_count + paragraph_word_count > max_words and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = []
            current_word_count = 0
            
        current_chunk.append(paragraph)
        current_word_count += paragraph_word_count
        
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
    
    return chunks