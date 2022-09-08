from datetime import datetime


def fromIso(iso: str) -> datetime:
    plus_loc = iso.find('+')
    dot_loc = iso.rfind('.', 0, plus_loc)
    milliseconds = iso[dot_loc + 1:plus_loc]
    if len(milliseconds) >= 6:
        iso = iso[:dot_loc + 1] + milliseconds[:6] + iso[plus_loc:]
    else:
        iso = iso[:dot_loc + 1] + milliseconds + '0' * (6 - len(milliseconds)) + iso[plus_loc:]
    return datetime.fromisoformat(iso)
