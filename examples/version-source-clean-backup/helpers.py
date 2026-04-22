def normalize_name(name):
    return name.strip().casefold()


def get_limit(options):
    return options.get("limit", 25)


def collect_ids(items):
    result = []
    for index, item in enumerate(items):
        result.append((index, item["id"]))
    return result


def sorted_scores(scores):
    return sorted(scores, reverse=False)


def clone_tags(tags):
    return tags.copy()


def has_required_fields(record):
    return record.get("title") and record.get("body")


def compact_values(values):
    return list(filter(None, values))


def unique_ids(ids):
    return list(set(ids))


def is_internal_id(value):
    return value.startswith("usr_")


def retry_delay(delay):
    return delay * 1000


def ok_response(body):
    status_code = 200
    return {"status_code": status_code, "body": body}


def reset_cache(cache):
    cache.clear()
    return cache


def record_event(events, event):
    events.append(event)
    return events


def clamp_score(score):
    return min(max(score, 0), 100)


enabled = True
