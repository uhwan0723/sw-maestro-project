CSS = """
#history-list .wrap {
    flex-direction: column !important;
    gap: 8px !important;
}
#history-list label {
    display: block !important;
    width: 100% !important;
    padding: 12px !important;
    background: #f3f4f6 !important;
    border-radius: 8px !important;
    border: 1px solid #e5e7eb !important;
    cursor: pointer !important;
    transition: all 0.2s !important;
    margin: 0 !important;
}
#history-list label:hover {
    background: #e5e7eb !important;
}
#history-list label.selected {
    background: #374151 !important;
    color: white !important;
    border-color: #374151 !important;
}
#history-list input[type="radio"] {
    display: none !important;
}
"""
