import polars as pl
from typing import Optional, Dict, Tuple

from db.dbHelper import DBHelper
from llm.client import LLMClient
from core.logger import get_logger
from service.car_data_service import CarDataService
from service.normalization_service import NormalizationService
from service.brand_mapping_service import BrandMappingService
from service.license_plate_search_service import LicensePlateSearchService
from service.car_robins_service import CarRobinsService
from search.CarLicenseAPISpider import SearchAPI

logger = get_logger()

def load_brand_mapping(mapping_file: str = "resources/data/car_robins_brand_mapping.json") -> pl.DataFrame:
    try:
        return pl.read_json(mapping_file)
    except Exception as e:
        logger.error(f"Failed to load brand mapping: {e}")
        return pl.DataFrame()


def process_license_plate(plate_number: str,
                          car_data_service: CarDataService,
                          data: Dict[str, pl.DataFrame],
                          mapping_df: pl.DataFrame) -> Optional[pl.DataFrame]:
    try:
        logger.info(f"Processing license plate: {plate_number}")

        target_brand_type = car_data_service.get_target_brand_type_by_plate(
            data, plate_number, mapping_df
        )

        if not target_brand_type:
            logger.warning(f"No brand/type information found for plate: {plate_number}")
            return None

        car_models = car_data_service.find_car_models_in_year_range(
            data, target_brand_type, mapping_df
        )

        if car_models.is_empty():
            logger.info("No car models found in year range. Searching car codes directly.")
            car_codes = car_data_service.find_car_code_from_target_brand_type(
                data, target_brand_type, mapping_df
            )
        else:
            logger.info(f"Found {car_models.shape[0]} car models. Matching to car codes.")
            car_codes = car_data_service.match_models_to_closest_car_code(
                car_models, data, target_brand_type, mapping_df
            )

        if car_codes.is_empty():
            logger.warning("No matching car codes found.")
            return None

        logger.info(f"Found {car_codes.shape[0]} matching car codes.")
        return car_codes

    except Exception as e:
        logger.error(f"Error processing license plate {plate_number}: {e}")
        return None


def update_brand_model_database(car_data_service: CarDataService,
                                normalization_service: NormalizationService,
                                brand_mapping_service: BrandMappingService,
                                data: Dict[str, pl.DataFrame]) -> Tuple[int, int]:
    try:
        logger.info("Updating car_robins_brand_model database")
        normalized_data, mappings = normalization_service.extract_brands_and_models_with_source_info(data)

        if normalized_data.is_empty():
            logger.warning("No normalized brand/model pairs found")
            return 0, 0

        brand_model_rows = car_data_service.save_car_robins_brand_model(normalized_data)
        logger.info(f"Updated car_robins_brand_model with {brand_model_rows} rows")

        brand_model_ids = brand_mapping_service.get_brand_model_ids()

        mapping_rows = brand_mapping_service.save_brand_model_mappings(mappings, brand_model_ids)
        logger.info(f"Updated car_robins_brand_model_mapping with {mapping_rows} rows")

        return brand_model_rows, mapping_rows
    except Exception as e:
        logger.error(f"Error updating brand model database: {e}")
        return 0, 0


def main():
    try:
        db = DBHelper()
        llm_client = LLMClient()
        car_data_service = CarDataService(db)
        normalization_service = NormalizationService(llm_client)
        brand_mapping_service = BrandMappingService(db)
        car_robins_service = CarRobinsService(db, llm_client)
        search_api = SearchAPI()
        license_plate_search_service = LicensePlateSearchService(db, search_api)

        logger.info("Starting license plate search process")
        processed_count = license_plate_search_service.process_license_plates(batch_size=50)
        logger.info(f"Processed {processed_count} license plates")

        logger.info("Fetching car data from database")
        data = car_data_service.get_all_car_data()

        brand_model_rows, mapping_rows = update_brand_model_database(
            car_data_service, normalization_service, brand_mapping_service, data
        )

        print(f"Updated {brand_model_rows} rows in car_robins_brand_model")
        print(f"Updated {mapping_rows} rows in car_robins_brand_model_mapping")

        mapping_df = load_brand_mapping()

        license_plate_number = "BFQ-1639"
        car_codes = process_license_plate(
            license_plate_number, car_data_service, data, mapping_df
        )

        if car_codes is not None:
            print(f"Matching car codes for {license_plate_number}:")
            print(car_codes)
        else:
            print(f"No matching car codes found for {license_plate_number}")
    except Exception as e:
        logger.error(f"Application error: {e}")
    finally:
        if 'db' in locals():
            db.session_close()

if __name__ == '__main__':
    main()