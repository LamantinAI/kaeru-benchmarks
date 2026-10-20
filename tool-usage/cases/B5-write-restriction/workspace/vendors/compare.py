def compare(vendors):
    return sorted(vendors, key=lambda vendor: vendor.get('integration_effort', 0))
