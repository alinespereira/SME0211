MODULES := simplex printing_company
PDOC := uv run pdoc --math -t pdoc-templates

.PHONY: docs serve

docs:
	$(PDOC) $(MODULES) -o docs/api

serve: docs
	$(PDOC) $(MODULES)