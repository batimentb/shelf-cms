config = {
    "name": "Dashboard",
    "description": "Dashboard-like view using tiles containing text and chart.",
    "extend": {
        "view": {
            "admin.index": {
                "tail_js": "tail",
                "head_css": "head"
            },
        }
    }
}
