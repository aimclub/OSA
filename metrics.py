import re
import sys
import zlib

from bert_score import score


# Calculate number of syllables in docstring
def _count_syllables(word):
    # Remove punctuation
    word = re.sub(r'[^a-zA-Z]', '', word)
    
    # Vowel count
    vowels = 'aeiouy'
    syllables = 0
    last_was_vowel = False
    for char in word:
        if char.lower() in vowels:
            if not last_was_vowel:
                syllables += 1
            last_was_vowel = True
        else:
            last_was_vowel = False
    
    # Adjust syllable count for words ending in 'e'
    if word.endswith(('e', 'es', 'ed')):
        syllables -= 1
    
    # Adjust syllable count for words with no vowels
    if syllables == 0:
        syllables = 1
    
    return syllables

# Calculate Flesch reading score
def flesch_reading_ease(text):
    sentences = text.count('.') + text.count('!') + text.count('?') + 1
    words = len(re.findall(r'\b\w+\b', text))
    syllables = sum(_count_syllables(word) for word in text.split())
    
    # Calculate Flesch Reading Ease score
    score = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
    
    return score

def calculate_bert_score(docstring1, docstring2):
    # Calculate BERT score
    _, _, bert_score_f1 = score([docstring1], [docstring2], lang='en', model_type='bert-base-uncased')

    return bert_score_f1.item()

def calculate_concise(docstring1, docstring2):
    # Calculate concise score based on length difference
    d1 = zlib.compress(docstring1.encode())
    d2 = zlib.compress(docstring2.encode())
    
    if d2 == 0:
        return 0.0

    return sys.getsizeof(d1)/ sys.getsizeof(d2)  # noqa: F821
