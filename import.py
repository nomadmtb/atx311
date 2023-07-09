import argparse
import csv
import dataclasses
import datetime
import itertools
import io
import json
import pathlib
import re
from typing import Any, Dict, Callable, Generator, Optional, Tuple

import requests


ELASTICSEARCH_ENDPOINT = "http://localhost:9200"
CSV_DOWNLOAD_ENDPOINT = "https://data.austintexas.gov/api/views/xwdj-i9he/rows.csv"


@dataclasses.dataclass
class MappedField:
    new_name: str
    es_format: Dict[str, Any]
    row_formatter: Callable


@dataclasses.dataclass
class HydratedDocumentResponse:
    field_mapping: MappedField
    document: Dict[str, Any]


def coordinates(input_str: str) -> Optional[str]:
    pattern = r"^\((\d+\.\d+), (-+\d+\.\d+)\)$"
    match = re.match(pattern, input_str)
    if match and len(match.groups()) == 2:
        lat, lon = match.groups()
        return f"{lat},{lon}"
    return None


ROW_TO_FIELD = {
    "Service Request (SR) Number": MappedField(
        "sr_req_number",
        {"type": "keyword"},
        str,
    ),
    "SR Description": MappedField(
        "sr_req_description",
        {"type": "keyword"},
        str,
    ),
    "Method Recieved": MappedField(
        "sr_req_method_recieved",
        {"type": "keyword"},
        str,
    ),
    "SR Status": MappedField(
        "sr_req_status",
        {"type": "keyword"},
        str,
    ),
    "Status Change Date": MappedField(
        "sr_req_status_change_date",
        {"type": "date", "format": "MM/dd/yyyy HH:mm:ss a"},
        str,
    ),
    "Created Date": MappedField(
        "timestamp",
        {"type": "date", "format": "MM/dd/yyyy HH:mm:ss a"},
        str,
    ),
    "Last Update Date": MappedField(
        "sr_req_last_updated_date",
        {"type": "date", "format": "MM/dd/yyyy HH:mm:ss a"},
        str,
    ),
    "Close Date": MappedField(
        "sr_req_closed_date",
        {"type": "date", "format": "MM/dd/yyyy HH:mm:ss a"},
        str,
    ),
    "SR Location": MappedField(
        "sr_req_location",
        {"type": "text"},
        str,
    ),
    "Council District": MappedField(
        "sr_req_council_district_number",
        {"type": "integer"},
        int,
    ),
    "Latitude Coordinate": MappedField(
        "sr_req_latitude_coordinate",
        {"type": "float"},
        float,
    ),
    "Longitude Coordinate": MappedField(
        "sr_req_longitude_coordinate",
        {"type": "float"},
        float,
    ),
    "(Latitude.Longitude)": MappedField(
        "sr_req_coordinates",
        {"type": "geo_point"},
        coordinates,
    ),
}

INDEX_MAPPINGS = {
    "mappings": {"properties": {v.new_name: v.es_format for v in ROW_TO_FIELD.values()}}
}


def _document_to_index_name(doc: Dict[str, Any]) -> str:
    created_dt = datetime.datetime.strptime(doc["timestamp"], "%m/%d/%Y %I:%M:%S %p")
    return f"atx311-{created_dt.year}-{created_dt.month:02d}"


def _document_from_row(row: Dict[str, Any]) -> HydratedDocumentResponse:
    document = {}
    for column_name, mapping in ROW_TO_FIELD.items():
        if column_name in row:
            document[mapping.new_name] = (
                (mapping.row_formatter)(row[column_name]) if row[column_name] else None
            )
    return HydratedDocumentResponse(field_mapping=mapping, document=document)


def _csv_api_iter() -> Generator[HydratedDocumentResponse, None, None]:
    print(f'fetching latest 311 data from "{CSV_DOWNLOAD_ENDPOINT}"...')
    with requests.get(
        CSV_DOWNLOAD_ENDPOINT,
        params={"accessType": "DOWNLOAD"},
        stream=True,
    ) as resp:
        reader = csv.DictReader(resp.iter_lines(decode_unicode=True))
        for row in reader:
            yield _document_from_row(row)


def _csv_file_iter(
    path: pathlib.Path,
) -> Generator[HydratedDocumentResponse, None, None]:
    print("fetching 311 data from local file...")
    with open(path) as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            yield _document_from_row(row)


def _documents_iter(
    args: argparse.Namespace,
) -> Generator[HydratedDocumentResponse, None, None]:
    return _csv_file_iter(args.path) if args.path else _csv_api_iter()


def _index_documents(docs_chunk: Tuple[HydratedDocumentResponse]) -> None:
    buffer = io.StringIO()
    for doc_res in docs_chunk:
        index = _document_to_index_name(doc_res.document)
        buffer.write(json.dumps({"index": {"_index": index}}) + "\n")
        buffer.write(json.dumps(doc_res.document) + "\n")
    res = requests.post(
        f"{ELASTICSEARCH_ENDPOINT}/_bulk",
        data=buffer.getvalue(),
        headers={"Content-Type": "application/x-ndjson"},
    )
    res.raise_for_status()


def _create_index_template() -> None:
    req_body = {"index_patterns": ["atx311-*"], **INDEX_MAPPINGS}
    res = requests.put(f"{ELASTICSEARCH_ENDPOINT}/_template/atx311", json=req_body)
    res.raise_for_status()


def _import(args: argparse.Namespace, index_chunksize=250) -> None:
    print("creating index template...")
    _create_index_template()

    print("indexing documents...")
    docs_iterator = _documents_iter(args)

    while True:
        chunk = tuple(itertools.islice(docs_iterator, index_chunksize))
        if not chunk:
            break
        _index_documents(chunk)


def _ensure_path(input_data: str) -> pathlib.Path:
    path = pathlib.Path(input_data).resolve().absolute()
    if not path.exists():
        raise ValueError("does not exist")
    return path


def _get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", help="Path to csv", type=_ensure_path, required=False)
    return parser.parse_args()


def main() -> None:
    args = _get_args()
    _import(args)


if __name__ == "__main__":
    main()
