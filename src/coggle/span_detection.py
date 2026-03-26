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
        spans[-1].append(token)
    print("Root verb: " + root_verb)
    print(spans)
