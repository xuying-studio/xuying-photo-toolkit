from xuying_toolbox.domain.services.xmp import (
    XMP_JPEG_HEADER,
    find_jpeg_segment,
    insert_jpeg_xmp,
    read_properties,
    update_properties,
)

MINIMAL_JPEG = b"\xff\xd8\xff\xd9"


def test_reads_decimal_rating_and_html_label_from_attributes() -> None:
    content = (
        b"<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' "
        b"xmlns:xmp='http://ns.adobe.com/xap/1.0/'>"
        b'<rdf:Description xmp:Rating="2.0" xmp:Label="Blue &amp; Green" />'
        b"</rdf:RDF>"
    )

    properties = read_properties(content)

    assert properties.rating == 2
    assert properties.label == "Blue & Green"


def test_invalid_rating_is_normalized_to_zero() -> None:
    assert read_properties(b"<xmp:Rating>6</xmp:Rating>").rating == 0
    assert read_properties(b"<xmp:Rating>-1</xmp:Rating>").rating == 0


def test_update_self_closing_description_preserves_other_fields() -> None:
    content = (
        b"<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' "
        b"xmlns:xap='http://ns.adobe.com/xap/1.0/'>"
        b"<rdf:Description xap:CreatorTool='Adobe Bridge' />"
        b"</rdf:RDF>"
    )

    updated = update_properties(content, 5, "Approved")

    assert b"xap:CreatorTool='Adobe Bridge'" in updated
    assert b"<xap:Rating>5</xap:Rating>" in updated
    assert b"<xap:Label>Approved</xap:Label>" in updated


def test_jpeg_segment_length_matches_payload() -> None:
    content = insert_jpeg_xmp(MINIMAL_JPEG, 4, "Select")

    segment = find_jpeg_segment(content)

    assert segment is not None
    assert segment.payload.startswith(XMP_JPEG_HEADER)
    stored_length = int.from_bytes(content[segment.start + 2 : segment.start + 4], "big")
    assert stored_length == len(segment.payload) + 2
