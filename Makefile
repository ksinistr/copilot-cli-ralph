build:
	docker build -t simple-copilot-ralph .

run:
	docker run -it --rm \
	  -v "$$(pwd):/workspace" \
	  -v "$$HOME/.config/github-copilot:/root/.config/github-copilot:ro" \
	  -v "$$HOME/.config/gh:/root/.config/gh:ro" \
	  -e GH_TOKEN=$$(gh auth token) \
	  simple-copilot-ralph
