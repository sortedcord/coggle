from dataclasses import dataclass

"""
This resolver should receive a ParsedResponse object and would "resolve" that to send it to the executor
"""
@dataclass
class ResolvedCommand:
    """
    What the executor would need:
    - adapter ("ls", "mv", "cp", "ffmpeg")
    - path
    - flags
    - filters
    ...
    """
    pass
