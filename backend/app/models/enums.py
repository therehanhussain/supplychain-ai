"""Manufacturing and Material Traceability Enums."""
import enum


class UnitOfMeasure(str, enum.Enum):
    """Standard manufacturing units of measure."""
    KG = "kg"
    G = "g"
    LITRE = "litre"
    METER = "meter"
    PIECE = "piece"
    BOX = "box"
    ROLL = "roll"
    SHEET = "sheet"


class MaterialCategory(str, enum.Enum):
    """Material and product classifications."""
    RAW_MATERIAL = "RAW_MATERIAL"
    COMPONENT = "COMPONENT"
    FINISHED_GOOD = "FINISHED_GOOD"
    OTHER = "OTHER"


class ProductionOrderStatus(str, enum.Enum):
    """Lifecycle states of a production order."""
    PLANNED = "PLANNED"
    RELEASED = "RELEASED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class WorkOrderStatus(str, enum.Enum):
    """Lifecycle states of a discrete work order operation."""
    PLANNED = "PLANNED"
    RELEASED = "RELEASED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TransactionType(str, enum.Enum):
    """Manufacturing stock transaction types.

    Movement Directions:
    - RECEIPT: External/Supplier -> Warehouse Store (+ inventory)
    - ISSUE: Warehouse Store -> Production / Employee Holding (- inventory, + req.issued_quantity)
    - CONSUMPTION: Production / Employee -> Finished Good Assembly (+ req.consumed_quantity)
    - RETURN: Production / Employee Holding -> Warehouse Store (+ inventory, + req.returned_quantity)
    - TRANSFER_OUT: Source Warehouse -> In-Transit (- source inventory)
    - TRANSFER_IN: In-Transit -> Destination Warehouse (+ dest inventory)
    - WASTAGE: Production scrap or store loss (+ req.wastage_quantity or - inventory, reason mandatory)
    - DAMAGE: Stock damaged in handling (- inventory, reason mandatory)
    - EXPIRY: Stock expired/spoiled (- inventory, reason mandatory)
    - ADJUSTMENT: Physical audit count reconciliation (+/- inventory, reason mandatory)
    """
    RECEIPT = "RECEIPT"
    ISSUE = "ISSUE"
    CONSUMPTION = "CONSUMPTION"
    RETURN = "RETURN"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    WASTAGE = "WASTAGE"
    DAMAGE = "DAMAGE"
    EXPIRY = "EXPIRY"
    ADJUSTMENT = "ADJUSTMENT"
