import spacy

def output_normalizer(spans) -> list[list[str]]:
    return [[token.text for token in span] for span in spans]

def span_splitter(spacy_doc):
    spans = [[]]
    root_verb = ""
    # remove verb
    cct_verb = False
    for token in spacy_doc:
        if (token.pos_ == "VERB" or token.text == "rename") and not cct_verb:
            root_verb = token.text
            cct_verb = True
            continue
        # if token is PART then new span
        if token.pos_ == "PART":
            spans.append([])
        # if token is verb and previous token was PART then same span
        if token.pos_ == "VERB" and spans[-1] and spans[-1][-1].pos_ == "PART":
            spans[-1].append(token)
            continue
        # if current token is ADJ and previous token was NOUN then different span
        if token.pos_ == "ADJ" and spans[-1] and spans[-1][-1].pos_ == "NOUN":
            spans.append([])
        # if the token is "than" then same span
        if token.text == "than":
            spans[-1].append(token)
            continue
        # if current token is ADP but previous token was VERB then same span
        if token.pos_ == "ADP" and spans[-1] and spans[-1][-1].pos_ == "VERB":
            spans[-1].append(token)
            continue
        if token.pos_ == "ADP" or token.pos_ == "VERB":
            spans.append([])
        spans[-1].append(token)
    return output_normalizer(spans)


def run_nlp(query: str):
    nlp = spacy.load("en_core_web_sm")

    return nlp(query)

def detect_spans(query: str) -> list[list[str]]:
    return span_splitter(run_nlp(query))