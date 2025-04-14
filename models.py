from sqlmodel import Field, Relationship, SQLModel

from typing import Optional, List
from datetime import datetime, date


class CarBrand(SQLModel, table=True):
    __tablename__ = "car_brand"

    code1: str = Field(max_length=126, primary_key=True)
    name: Optional[str] = Field(default=None, max_length=126)


class CarType(SQLModel, table=True):
    __tablename__ = "car_type"

    code1: str = Field(max_length=126, primary_key=True)
    code2: str = Field(max_length=126, primary_key=True)
    category: Optional[str] = Field(default=None, max_length=126)
    kind: Optional[str] = Field(default=None, max_length=126)


class CarModel(SQLModel, table=True):
    __tablename__ = "car_model"

    brand: str = Field(max_length=126, primary_key=True)
    year: str = Field(max_length=126, primary_key=True)
    model: str = Field(max_length=126, primary_key=True)
    style: str = Field(max_length=126, primary_key=True)
    from_url: str = Field(max_length=126)

    door: Optional[str] = Field(default=None, max_length=126)
    seat: Optional[str] = Field(default=None, max_length=126)
    displacement: Optional[str] = Field(default=None, max_length=126)
    power: Optional[str] = Field(default=None, max_length=126)
    fuel: Optional[str] = Field(default=None, max_length=126)

    list_price: Optional[float] = Field(default=None)
    create_ts: Optional[datetime] = Field(default=None)
    code: Optional[str] = Field(default=None, max_length=126)
    match: Optional[float] = Field(default=None)
    version: Optional[str] = Field(default=None, max_length=126)


class CarCode(SQLModel, table=True):
    __tablename__ = "car_code"

    code1: str = Field(max_length=126, primary_key=True)
    code2: str = Field(max_length=126, primary_key=True)
    code3: str = Field(max_length=126, primary_key=True)
    code4: str = Field(max_length=126, primary_key=True)

    type: Optional[str] = Field(default=None, max_length=126)
    reset_price: Optional[int] = Field(default=None)

    feecode_car: Optional[str] = Field(default=None, max_length=126)
    feecode_theft: Optional[str] = Field(default=None, max_length=126)
    feecode_date: Optional[date] = Field(default=None)

    reset_price2: Optional[int] = Field(default=None)
    feecode_car2: Optional[str] = Field(default=None, max_length=126)
    feecode_theft2: Optional[str] = Field(default=None, max_length=126)
    feecode_date2: Optional[date] = Field(default=None)

    reset_price3: Optional[int] = Field(default=None)
    feecode_car3: Optional[str] = Field(default=None, max_length=126)
    feecode_theft3: Optional[str] = Field(default=None, max_length=126)
    feecode_date3: Optional[date] = Field(default=None)

    reset_price4: Optional[int] = Field(default=None)
    feecode_car4: Optional[str] = Field(default=None, max_length=126)
    feecode_theft4: Optional[str] = Field(default=None, max_length=126)
    feecode_date4: Optional[date] = Field(default=None)

    reset_price5: Optional[int] = Field(default=None)
    feecode_car5: Optional[str] = Field(default=None, max_length=126)
    feecode_theft5: Optional[str] = Field(default=None, max_length=126)
    feecode_date5: Optional[date] = Field(default=None)

    created_date: Optional[date] = Field(default=None)
    memo: Optional[str] = Field(default=None)
    updated_date: Optional[date] = Field(default=None)
    data_date: Optional[date] = Field(default=None)


class CarLicensePlateInfo(SQLModel, table=True):
    __tablename__ = "car_license_plate_info"
    id: int = Field(primary_key=True)

    car_number: Optional[str] = Field(default=None, max_length=255)
    current_car_number: Optional[str] = Field(default=None, max_length=255)
    previous_car_number: Optional[str] = Field(default=None, max_length=255)
    valid_date_of_business_license: Optional[str] = Field(default=None, max_length=255)
    license_status: Optional[str] = Field(default=None, max_length=255)
    status_date: Optional[str] = Field(default=None, max_length=255)
    category: Optional[str] = Field(default=None, max_length=255)
    fuel: Optional[str] = Field(default=None, max_length=255)
    brand: Optional[str] = Field(default=None, max_length=255)
    type: Optional[str] = Field(default=None, max_length=255)
    manu_date: Optional[str] = Field(default=None, max_length=255)
    color: Optional[str] = Field(default=None, max_length=255)
    style: Optional[str] = Field(default=None, max_length=255)
    displacement: Optional[str] = Field(default=None, max_length=255)
    current_jurisdiction: Optional[str] = Field(default=None, max_length=255)
    licensing_date: Optional[str] = Field(default=None, max_length=255)
    original_photo_date: Optional[str] = Field(default=None, max_length=255)
    replacement_photo_date: Optional[str] = Field(default=None, max_length=255)
    next_inspection_date: Optional[str] = Field(default=None, max_length=255)
    delay_application: Optional[str] = Field(default=None, max_length=255)
    chattel_security_date: Optional[str] = Field(default=None, max_length=255)
    chattel_security_times: Optional[str] = Field(default=None, max_length=255)
    buckle_until_date: Optional[str] = Field(default=None, max_length=255)
    prohibition_of_changes: Optional[str] = Field(default=None, max_length=255)
    environmental_violations: Optional[str] = Field(default=None, max_length=255)
    violation_of_mandatory_liability_insurance: Optional[str] = Field(
        default=None, max_length=255
    )
    violation_of_section_of_the_highway_act: Optional[str] = Field(
        default=None, max_length=255
    )
    outstanding_traffic_violations: Optional[str] = Field(default=None, max_length=255)
    licence_tax_owed: Optional[str] = Field(default=None, max_length=255)
    violation_of_license_tax_laws: Optional[str] = Field(default=None, max_length=255)
    fuel_bills_in_arrears: Optional[str] = Field(default=None, max_length=255)
    created_ts: Optional[datetime] = Field(default_factory=datetime.now)
    updated_ts: Optional[datetime] = Field(default_factory=datetime.now)


class CarRobinsBrandModel(SQLModel, table=True):
    __tablename__ = "car_robins_brand_model"

    id: Optional[int] = Field(default=None, primary_key=True)
    brand: str
    model: str
    create_ts: Optional[datetime] = Field(default_factory=datetime.now)

    mappings: List["CarRobinsBrandModelMapping"] = Relationship(
        back_populates="brand_model"
    )


class CarRobinsBrandModelMapping(SQLModel, table=True):
    __tablename__ = "car_robins_brand_model_mapping"

    id: Optional[int] = Field(default=None, primary_key=True)
    source: str
    source_brand: str
    source_type: str
    brand_model_id: int = Field(foreign_key="car_robins_brand_model.id")
    create_ts: Optional[datetime] = Field(default_factory=datetime.now)

    brand_model: Optional[CarRobinsBrandModel] = Relationship(back_populates="mappings")


class CarRobinsSearchResult(SQLModel, table=True):
    __tablename__ = "car_robins_search_result"

    id: Optional[int] = Field(default=None, primary_key=True)
    source: str
    source_brand: str
    source_type: str
    result: str
    create_ts: Optional[datetime] = Field(default_factory=datetime.now)


class CarRobinsLLMFailure(SQLModel, table=True):
    __tablename__ = "car_robins_llm_failure"

    id: Optional[int] = Field(default=None, primary_key=True)
    source: str
    source_brand: str
    source_type: str
    create_ts: Optional[datetime] = Field(default_factory=datetime.now)
    update_ts: Optional[datetime] = Field(default_factory=datetime.now)
