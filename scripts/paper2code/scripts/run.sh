#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Set default values if not provided by environment variables
: "${PAPER_NAME:=Transformer}"
: "${PDF_PATH:=$SCRIPT_DIR/../examples/Transformer.pdf}"
: "${OUTPUT_DIR:=$SCRIPT_DIR/../outputs/$PAPER_NAME}"
: "${OUTPUT_REPO_DIR:=$SCRIPT_DIR/../outputs/${PAPER_NAME}_repo}"

PDF_JSON_PATH="$OUTPUT_DIR/${PAPER_NAME}.json"
PDF_JSON_CLEANED_PATH="$OUTPUT_DIR/${PAPER_NAME}_cleaned.json"

mkdir -p "$OUTPUT_DIR"
mkdir -p "$OUTPUT_REPO_DIR"

echo "$PAPER_NAME"

echo "------- Preprocess -------"

python "$SCRIPT_DIR/../codes/0_pdf_process.py" \
    --input_json_path "${PDF_JSON_PATH}" \
    --output_json_path "${PDF_JSON_CLEANED_PATH}"

echo "------- PaperCoder -------"

python "$SCRIPT_DIR/../codes/1_planning.py" \
    --paper_name "$PAPER_NAME" \
    --pdf_json_path "${PDF_JSON_CLEANED_PATH}" \
    --output_dir "${OUTPUT_DIR}"

python "$SCRIPT_DIR/../codes/1.1_extract_config.py" \
    --paper_name "$PAPER_NAME" \
    --output_dir "${OUTPUT_DIR}"

cp -rp "${OUTPUT_DIR}/planning_config.yaml" "${OUTPUT_REPO_DIR}/config.yaml"

python "$SCRIPT_DIR/../codes/2_analyzing.py" \
    --paper_name "$PAPER_NAME" \
    --pdf_json_path "${PDF_JSON_CLEANED_PATH}" \
    --output_dir "${OUTPUT_DIR}"

python "$SCRIPT_DIR/../codes/3_coding.py"  \
    --paper_name "$PAPER_NAME" \
    --pdf_json_path "${PDF_JSON_CLEANED_PATH}" \
    --output_dir "${OUTPUT_DIR}" \
    --output_repo_dir "${OUTPUT_REPO_DIR}"
