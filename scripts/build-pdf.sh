#!/bin/sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
cd "$repo_root"

# Load PDF settings from .env without executing arbitrary shell code.
# Explicit environment variables take precedence over values in .env.
if test -f .env; then
  while IFS= read -r setting; do
    setting=$(printf '%s' "$setting" | sed 's/\r$//')
    case "$setting" in
      PDF_NAME=*)
        test "${PDF_NAME+x}" = x || PDF_NAME=${setting#PDF_NAME=}
        ;;
      PDF_VERSION=*)
        test "${PDF_VERSION+x}" = x || PDF_VERSION=${setting#PDF_VERSION=}
        ;;
    esac
  done < .env
fi

: "${PDF_NAME:=polymaker-filament-preset-tuning-guide}"
: "${PDF_VERSION:=local}"
pdf_stem=${PDF_NAME%.pdf}
pdf_output="${pdf_stem}-${PDF_VERSION}.pdf"

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
  # Strip a possible carriage return when the manifest uses Windows line endings.
  document=$(printf '%s' "$document" | sed 's/\r$//')
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
  --from=markdown+pipe_tables+strikeout+task_lists+autolink_bare_uris+tex_math_dollars+raw_tex+raw_attribute+header_attributes-smart \
  --resource-path=docs \
  --pdf-engine=xelatex \
  --toc \
  --number-sections \
  --metadata title="Polymaker Filament Preset Tuning Guide" \
  --metadata author="Polymaker" \
  --metadata date="Release ${PDF_VERSION}" \
  --variable mainfont="Cambria" \
  --variable CJKmainfont="SimSun" \
  --variable geometry:margin=3cm \
  --variable linestretch=1.2 \
  --variable fontsize=10.5pt \
  --output "dist/${pdf_output}"

test -s "dist/${pdf_output}"
echo "PDF generated: dist/${pdf_output}"
