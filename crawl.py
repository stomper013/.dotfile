import logging
from concurrent.futures import ThreadPoolExecutor
import psycopg2
from psycopg2.extras import execute_batch
from vnstock import *
import pandas as pd
from datetime import datetime
import json
from const import VN30, VN100
import signal
import pickle
import os

main_logger = logging.getLogger()
main_logger.setLevel(logging.INFO)

os.makedirs("logs", exist_ok=True)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)

main_logger.addHandler(console_handler)

DB_CONFIG = {
    "dbname": "stockgpt-trading",
    "user": "admin",
    "password": "dev",
    "host": "localhost",
}

CHUNK_SIZE = 1000
MAX_WORKERS = 4

_INTERVAL_MAP = {
    "1m": "1m",
    "1h": "1H",
    "1d": "1D",
}


class StockDataProcessor:
    def __init__(self):
        self.vnstock = Vnstock()
        self.conn = self._create_db_connection()
        self.log_dir = "logs"
        self.progress_file = os.path.join(self.log_dir, "progress.json")
        self.checkpoint_file = os.path.join(self.log_dir, "checkpoint.pkl")
        self.stats = {
            "stock1m": {"processed": 0, "failed": 0},
            "stock1h": {"processed": 0, "failed": 0},
            "stock1d": {"processed": 0, "failed": 0},
        }
        self.is_running = True
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        os.makedirs(self.log_dir, exist_ok=True)

    def _create_db_connection(self):
        return psycopg2.connect(**DB_CONFIG)

    def _setup_logger(self, symbol):
        symbol_log_dir = os.path.join(self.log_dir, symbol)
        os.makedirs(symbol_log_dir, exist_ok=True)

        loggers = {}
        for interval in ["1m", "1h", "1d"]:
            logger_name = f"stock_logger_{symbol}_{interval}"
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.INFO)
            logger.handlers = []

            log_file = os.path.join(symbol_log_dir, f"{interval}_data_stock.log")
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)

            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(formatter)

            logger.addHandler(file_handler)
            logger.addHandler(logging.StreamHandler())

            loggers[f"stock{interval}"] = logger

        return loggers

    def _maintenance(self):
        tables = ["stock1d", "stock1h", "stock1m"]

        if self.conn:
            self.conn.close()

        try:
            maintenance_conn = psycopg2.connect(**DB_CONFIG)
            maintenance_conn.autocommit = True

            with maintenance_conn.cursor() as cur:
                for table in tables:
                    try:
                        cur.execute(f"VACUUM (VERBOSE, ANALYZE) {table};")
                        logging.getLogger().info(f"Completed maintenance for {table}")
                    except Exception as e:
                        logging.getLogger().error(
                            f"Maintenance error for {table}: {str(e)}"
                        )

        except Exception as e:
            logging.getLogger().error(f"Error during maintenance: {str(e)}")

        finally:
            if "maintenance_conn" in locals():
                maintenance_conn.close()
            self.conn = self._create_db_connection()

    def _save_progress(self, completed_symbols):
        with open(self.progress_file, "w") as f:
            json.dump({"completed": list(completed_symbols)}, f)

    def _load_progress(self):
        try:
            with open(self.progress_file, "r") as f:
                return set(json.load(f)["completed"])
        except:
            return set()

    def _signal_handler(self, signum, frame):
        main_logger = logging.getLogger()
        main_logger.info("Received interrupt signal. Gracefully shutting down...")
        self.is_running = False

    def _save_checkpoint(self, symbol, table_name, chunk_info):
        checkpoint = {
            "symbol": symbol,
            "table_name": table_name,
            "chunk_info": chunk_info,
            "timestamp": datetime.now(),
        }
        with open(self.checkpoint_file, "wb") as f:
            pickle.dump(checkpoint, f)

    def _load_checkpoint(self):
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, "rb") as f:
                    return pickle.load(f)
        except Exception as e:
            logging.error(f"Error loading checkpoint: {str(e)}")
        return None

    def _process_symbol(self, symbol):
        loggers = self._setup_logger(symbol)
        try:
            stock = self.vnstock.stock(symbol=symbol, source="VCI")

            data = {
                "stock1m": stock.quote.history(
                    start="2000-01-01", end="2025-03-02", interval=_INTERVAL_MAP["1m"]
                ),
                "stock1h": stock.quote.history(
                    start="2000-01-01", end="2025-03-02", interval=_INTERVAL_MAP["1h"]
                ),
                "stock1d": stock.quote.history(
                    start="2000-01-01", end="2025-03-02", interval=_INTERVAL_MAP["1d"]
                ),
            }

            for interval, df in data.items():
                if df is not None and not df.empty:
                    df["symbol"] = symbol
                    for col in ["open", "high", "low", "close"]:
                        df[col] = df[col].astype(float)
                    df["volume"] = df["volume"].astype(int)
                else:
                    loggers[interval].warning(
                        f"No data found for {symbol} in {interval}"
                    )
                    self.stats[interval]["failed"] += 1

            return data, loggers

        except Exception as e:
            main_logger = logging.getLogger()
            main_logger.error(f"Error processing {symbol}: {str(e)}")
            return None, loggers

    def _save_chunk(self, df_chunk, table_name, symbol, loggers):
        if not self.is_running:
            return 0

        logger = loggers[table_name]

        try:
            # Prepare data
            df_chunk = df_chunk.copy()
            df_chunk["datetime"] = pd.to_datetime(df_chunk["time"]).dt.tz_localize(None)
            df_chunk = df_chunk.sort_values("datetime")

            chunk_info = {
                "symbol": symbol,
                "table": table_name,
                "start_time": df_chunk["datetime"].min(),
                "end_time": df_chunk["datetime"].max(),
                "record_count": len(df_chunk),
            }

            logger.info(f"Processing chunk for {symbol} in {table_name}")
            # Save checkpoint
            self._save_checkpoint(symbol, table_name, chunk_info)

            data = [
                (
                    symbol,
                    row["datetime"],
                    float(row["open"]),
                    float(row["high"]),
                    float(row["low"]),
                    float(row["close"]),
                    int(row["volume"]) if pd.notna(row["volume"]) else 0,
                )
                for _, row in df_chunk.iterrows()
            ]

            if not data:
                logger.error("No valid records to insert")
                return 0

            with self.conn.cursor() as cur:
                # Create partitions
                unique_months = df_chunk["datetime"].dt.to_period("M").unique()
                for period in unique_months:
                    start_date = period.to_timestamp()
                    end_date = (period + 1).to_timestamp()
                    partition_name = f"{table_name}_{start_date.strftime('%Y_%m')}"

                    try:
                        cur.execute(
                            f"""
                            DO $$
                            BEGIN
                                IF NOT EXISTS (
                                    SELECT 1 FROM pg_class c
                                    JOIN pg_namespace n ON n.oid = c.relnamespace
                                    WHERE c.relname = '{partition_name}'
                                    AND n.nspname = 'public'
                                ) THEN
                                    CREATE TABLE {partition_name}
                                    PARTITION OF {table_name}
                                    FOR VALUES FROM (%s) TO (%s);
                                END IF;
                            END $$;
                            """,
                            (start_date, end_date),
                        )
                        self.conn.commit()
                    except Exception as e:
                        logger.error(
                            f"Error creating partition {partition_name}: {str(e)}"
                        )
                        continue

                # Insert data
                try:
                    execute_batch(
                        cur,
                        f"""
                        INSERT INTO {table_name}
                            (ticker, datetime, open, high, low, close, volume)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (ticker, datetime) 
                        DO UPDATE SET 
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume;
                        """,
                        data,
                        page_size=CHUNK_SIZE,
                    )

                    cur.execute(
                        f"""
                        SELECT COUNT(*) FROM {table_name}
                        WHERE ticker = %s
                        AND datetime BETWEEN %s AND %s;
                        """,
                        (symbol, chunk_info["start_time"], chunk_info["end_time"]),
                    )

                    processed_count = cur.fetchone()[0]
                    self.conn.commit()

                    logger.info(
                        f"Successfully processed {processed_count}/{chunk_info['record_count']} records "
                        f"for {symbol} in {table_name} "
                        f"(partition: {table_name}_{chunk_info['start_time'].strftime('%Y_%m')}) "
                        f"from {chunk_info['start_time']} to {chunk_info['end_time']}"
                    )

                    if processed_count > 0:
                        self.stats[table_name]["processed"] += processed_count
                        if os.path.exists(self.checkpoint_file):
                            os.remove(self.checkpoint_file)
                    else:
                        self.stats[table_name]["failed"] += len(data)

                    return processed_count

                except Exception as e:
                    self.conn.rollback()
                    logger.error(f"Error during data insertion: {str(e)}")
                    raise

        except Exception as e:
            logger.error(f"Error in _save_chunk: {str(e)}")
            self.stats[table_name]["failed"] += len(df_chunk)
            return 0

    def process_symbols(self, symbols):
        main_logger = logging.getLogger()
        completed = self._load_progress()
        symbols = [s for s in symbols if s not in completed]
        checkpoint = self._load_checkpoint()

        if checkpoint:
            main_logger.info(
                f"Resuming from checkpoint: Symbol={checkpoint['symbol']}, "
                f"Table={checkpoint['table_name']}, "
                f"Time range={checkpoint['chunk_info']['start_time']} to "
                f"{checkpoint['chunk_info']['end_time']}"
            )

        self.stats = {
            "stock1m": {"processed": 0, "failed": 0},
            "stock1h": {"processed": 0, "failed": 0},
            "stock1d": {"processed": 0, "failed": 0},
        }

        main_logger.info(f"Processing {len(symbols)} symbols")
        start_time = datetime.now()

        try:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                for result_tuple in executor.map(self._process_symbol, symbols):
                    if not self.is_running:
                        main_logger.info("Stopping processing due to interrupt...")
                        break

                    if result_tuple is not None:
                        result, loggers = result_tuple
                        symbol = None

                        for table_name, df in result.items():
                            if df is not None and not df.empty:
                                symbol = df["symbol"].iloc[0]
                                total_records = len(df)
                                processed_records = 0

                                # Check checkpoint for resuming
                                start_index = 0
                                if (
                                    checkpoint
                                    and symbol == checkpoint["symbol"]
                                    and table_name == checkpoint["table_name"]
                                ):
                                    checkpoint_start_time = checkpoint["chunk_info"][
                                        "start_time"
                                    ]
                                    start_index = df[
                                        df["time"] >= checkpoint_start_time
                                    ].index[0]
                                    main_logger.info(
                                        f"Resuming from index {start_index}"
                                    )

                                # Process chunks
                                for i in range(start_index, len(df), CHUNK_SIZE):
                                    if not self.is_running:
                                        # Save checkpoint before exit
                                        chunk_info = {
                                            "start_time": df.iloc[i]["time"],
                                            "end_time": df.iloc[
                                                min(i + CHUNK_SIZE, len(df) - 1)
                                            ]["time"],
                                        }
                                        self._save_checkpoint(
                                            symbol, table_name, chunk_info
                                        )
                                        main_logger.info(
                                            f"Saved checkpoint at index {i}"
                                        )
                                        return

                                    chunk = df.iloc[i : i + CHUNK_SIZE]
                                    processed = self._save_chunk(
                                        chunk, table_name, symbol, loggers
                                    )
                                    processed_records += processed

                                if processed_records == 0:
                                    self.stats[table_name]["failed"] += total_records

                        if symbol:
                            completed.add(symbol)
                            self._save_progress(completed)
                            if os.path.exists(self.checkpoint_file):
                                os.remove(self.checkpoint_file)

        except Exception as e:
            main_logger.error(f"Error during processing: {str(e)}")
            raise

        finally:
            duration = datetime.now() - start_time
            main_logger.info(f"Processing completed in {duration}")

            for table_name, stats in self.stats.items():
                main_logger.info(
                    f"{table_name}: Processed {stats['processed']} records, "
                    f"Failed {stats['failed']} records"
                )


def main():
    try:
        processor = StockDataProcessor()
        symbols = VN30
        processor.process_symbols(symbols)
        processor._maintenance()

    except Exception as e:
        logging.getLogger().error(f"Main error: {str(e)}")
    finally:
        if hasattr(processor, "conn") and processor.conn:
            processor.conn.close()


if __name__ == "__main__":
    main()
