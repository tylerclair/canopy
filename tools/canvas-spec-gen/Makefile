IMAGE_NAME = canvas-spec-gen
OUTPUT_FILE = canvas.openapi.yaml

.PHONY: build extract generate clean

build:
	podman build -f Containerfile -t $(IMAGE_NAME) .

extract:
	podman run --rm $(IMAGE_NAME) > $(OUTPUT_FILE)

generate: build extract

clean:
	podman rmi $(IMAGE_NAME)