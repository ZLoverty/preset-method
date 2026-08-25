#!/bin/sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
cd "$repo_root"

: "${PDF_NAME:=polymaker-filament-preset-tuning-guide-local.pdf}"

for command in pandoc xelatex sed mktemp; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "required command not found: $command" >&2
    exit 1
  }
done

mkdir -p dist
document_list=$(mktemp)
combined=$(mktemp)
trap 'rm -f "$document_list" "$combined"' 0 1 2 15

while IFS= read -r document; do
  case "$document" in
    ''|\#*) continue ;;
  esac
  test -f "$document" || {
    echo "document listed in docs/pdf-order.txt does not exist: $document" >&2
    exit 1
  }
  printf '%s\n' "$document" >> "$document_list"
done < docs/pdf-order.txt

test -s "$document_list" || {
  echo "docs/pdf-order.txt does not contain any documents" >&2
  exit 1
}

while IFS= read -r document; do
  # The source files use --- as visual separators; omit those lines in the PDF.
  sed '/^[[:space:]]*---[[:space:]]*$/d' "$document" >> "$combined"
  printf '\n\n' >> "$combined"
done < "$document_list"

pandoc "$combined" \
  --from=markdown+pipe_tables+strikeout+task_lists+autolink_bare_uris+tex_math_dollars+raw_tex+raw_attribute+header_attributes \
  --resource-path=docs \
  --pdf-engine=xelatex \
  --toc \
  --number-sections \
  --metadata title="Polymaker Filament Preset Tuning Guide" \
  --metadata author="Polymaker" \
  --variable mainfont="Noto Sans" \
  --variable CJKmainfont="Noto Sans CJK SC" \
  --output "dist/${PDF_NAME}"

test -s "dist/${PDF_NAME}"
echo "PDF generated: dist/${PDF_NAME}"
