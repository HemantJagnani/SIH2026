# API-First Decision Tree

As per the Eurostat guidelines for web scraping, we prioritize APIs to ensure stability.

Decision tree for source integration:

```text
Is an appropriate authorized API available?
        |
        +-- YES --> API adapter
        |
        +-- NO --> Is web collection permitted/authorized?
                       |
                       +-- YES --> Web adapter
                       |
                       +-- NO --> Do not collect
```

**Rule:** Never infer permission merely because a webpage is publicly visible.
