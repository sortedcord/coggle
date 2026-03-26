import spacy

def span_splitter(spacy_doc):
    spans = [[]]
    root_verb = ""
    # remove verb
    cct_verb = False
    for token in spacy_doc:
        if token.pos_ == "VERB" and not cct_verb:
            root_verb = token.text
            cct_verb = True
            continue
        if token.pos_ == "ADP" or token.pos_ == "VERB":
            spans.append([])
        spans[-1].append(token.text)
    return spans


def run_nlp(query: str):
    nlp = spacy.load("en_core_web_sm")

    return nlp(query)

def detect_spans(query: str) -> list[list[str]]:
    return span_splitter(run_nlp(query))