from __future__ import annotations

from django.db import migrations


CREATE_SQL = """
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE catalog_productprice
    ADD CONSTRAINT catalog_price_product_currency_no_overlap
    EXCLUDE USING gist (
        product_id WITH =,
        currency WITH =,
        tstzrange(effective_from, effective_until, '[)') WITH &&
    );

CREATE FUNCTION catalog_validate_listing_product() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.product_code IS DISTINCT FROM OLD.product_code THEN
        RAISE EXCEPTION 'listing product codes are immutable';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM catalog_listingkindpricemode
        WHERE listing_kind_id = NEW.listing_kind_id
          AND price_mode = NEW.price_mode
    ) THEN
        RAISE EXCEPTION 'listing product price mode must be supported by its listing kind';
    END IF;

    IF NEW.is_free AND EXISTS (
        SELECT 1
        FROM catalog_listingkind AS kind
        INNER JOIN catalog_vertical AS vertical ON vertical.id = kind.vertical_id
        WHERE kind.id = NEW.listing_kind_id
          AND vertical.slug = 'autos'
    ) THEN
        RAISE EXCEPTION 'autos products cannot be free';
    END IF;

    IF NEW.is_free AND EXISTS (
        SELECT 1
        FROM catalog_productprice
        WHERE product_id = NEW.id
          AND amount_minor <> 0
    ) THEN
        RAISE EXCEPTION 'free products must only have zero prices';
    END IF;

    IF NOT NEW.is_free AND EXISTS (
        SELECT 1
        FROM catalog_productprice
        WHERE product_id = NEW.id
          AND amount_minor = 0
    ) THEN
        RAISE EXCEPTION 'non-free products cannot have zero prices';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER catalog_listing_product_integrity_trigger
BEFORE INSERT OR UPDATE OF listing_kind_id, product_code, price_mode, is_free
ON catalog_listingproduct
FOR EACH ROW EXECUTE FUNCTION catalog_validate_listing_product();

CREATE FUNCTION catalog_validate_product_price() RETURNS trigger AS $$
DECLARE
    product_is_free boolean;
    product_vertical_slug varchar(50);
BEGIN
    SELECT product.is_free, vertical.slug
    INTO product_is_free, product_vertical_slug
    FROM catalog_listingproduct AS product
    INNER JOIN catalog_listingkind AS kind ON kind.id = product.listing_kind_id
    INNER JOIN catalog_vertical AS vertical ON vertical.id = kind.vertical_id
    WHERE product.id = NEW.product_id;

    IF product_is_free AND NEW.amount_minor <> 0 THEN
        RAISE EXCEPTION 'free products must only have zero prices';
    END IF;
    IF NOT product_is_free AND NEW.amount_minor = 0 THEN
        RAISE EXCEPTION 'non-free products cannot have zero prices';
    END IF;
    IF product_vertical_slug = 'autos' AND NEW.amount_minor = 0 THEN
        RAISE EXCEPTION 'autos products cannot have zero prices';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER catalog_product_price_integrity_trigger
BEFORE INSERT OR UPDATE OF product_id, amount_minor
ON catalog_productprice
FOR EACH ROW EXECUTE FUNCTION catalog_validate_product_price();
"""

DROP_SQL = """
DROP TRIGGER IF EXISTS catalog_product_price_integrity_trigger ON catalog_productprice;
DROP FUNCTION IF EXISTS catalog_validate_product_price();
DROP TRIGGER IF EXISTS catalog_listing_product_integrity_trigger ON catalog_listingproduct;
DROP FUNCTION IF EXISTS catalog_validate_listing_product();
ALTER TABLE catalog_productprice
    DROP CONSTRAINT IF EXISTS catalog_price_product_currency_no_overlap;
"""


def create_postgresql_integrity(apps, schema_editor) -> None:
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(CREATE_SQL)


def drop_postgresql_integrity(apps, schema_editor) -> None:
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(DROP_SQL)


class Migration(migrations.Migration):
    dependencies = [("catalog", "0004_productprice_catalog_product_price_currency_iso")]

    operations = [migrations.RunPython(create_postgresql_integrity, drop_postgresql_integrity)]
