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

        previous_token = spans[-1][-1] if spans[-1] else None 

        # if token is PART then new span
        if token.pos_ == "PART":
            spans.append([])
        # if token is verb and previous token was PART then same span
        elif token.pos_ == "VERB" and spans[-1] and previous_token.pos_ == "PART":
            spans[-1].append(token)
            continue
        # if current token is ADJ and previous token was NOUN then new span
        elif token.pos_ == "ADJ" and spans[-1] and previous_token.pos_ == "NOUN":
            spans.append([])
        # if the token is "than" then same span
        elif token.text == "than":
            spans[-1].append(token)
            continue
        # if current token is ADP but previous token was VERB then same span
        elif token.pos_ == "ADP" and spans[-1] and previous_token.pos_ == "VERB":
            spans[-1].append(token)
            continue
        # if current token is CCONJ and next token is VERB and has a dep of "conj" then new span
        elif token.pos_ == "CCONJ" and spans[-1]:
            next_token = token.nbor(1) if token.i + 1 < len(spacy_doc) else None
            if next_token and next_token.pos_ == "VERB" and next_token.dep_ == "conj":
                spans.append([])
        # if current token is ADP or (VERB and previous token is not CCONJ) then new span
        elif token.pos_ == "ADP" or (token.pos_ == "VERB" and (not spans[-1] or previous_token.pos_ != "CCONJ")):
            spans.append([])
        # if current token is ADV then new span
        elif token.pos_ == "ADV":
            spans.append([])
        spans[-1].append(token)
    # return output_normalizer(spans)
    return spans


def run_nlp(query: str):
    nlp = spacy.load("en_core_web_sm")

    return nlp(query)

def detect_spans(query: str) -> list[list[str]]:
    return span_splitter(run_nlp(query))

# Dependency tree builder
# Currently span detection only based on POS tags
# Maybe we can also make use of the dependency tree to avoid making special control flows for every edge case

def dependency_tree_builder(spacy_doc) -> dict:
    nodes = {token.i: {
        "text": token.text,
        "pos": token.pos_,
        "dep": token.dep_,
        "children": []
    } for token in spacy_doc}

    root = None
    for token in spacy_doc:
        if token.dep_ == "ROOT":
            root = token.i
        else:
            nodes[token.head.i]["children"].append(nodes[token.i])

    return nodes[root]