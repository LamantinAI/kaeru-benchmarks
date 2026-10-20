def apply_filters(rows, filters):
    return [row for row in rows if all(row.get(key) == value for key, value in filters.items())]

def order_results(rows):
    return list(rows)
