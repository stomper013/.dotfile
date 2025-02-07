import { MigrationInterface, QueryRunner } from 'typeorm';

export class InitStockData1738847581319 implements MigrationInterface {
  name = 'InitStockData1738847581319';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(
      `CREATE TABLE "stock1d" (
        "id" SERIAL, 
        "datetime" TIMESTAMP NOT NULL, 
        "ticker" character varying(12) NOT NULL, 
        "open" numeric(10,2) NOT NULL, 
        "high" numeric(10,2) NOT NULL, 
        "low" numeric(10,2) NOT NULL, 
        "close" numeric(10,2) NOT NULL, 
        "volume" bigint NOT NULL, 
        CONSTRAINT "stock1d_unique" UNIQUE ("ticker", "datetime"), 
        CONSTRAINT "PK_ad66689d82f4c4dc3ba24351d23" PRIMARY KEY ("id", "datetime")
      ) PARTITION BY RANGE (datetime)`,
    );
    await queryRunner.query(
      `CREATE INDEX "idx_stock1d_ticker_datetime" ON "stock1d" ("ticker", "datetime") `,
    );
    await queryRunner.query(
      `CREATE INDEX "idx_stock1d_datetime" ON "stock1d" ("datetime") `,
    );
    await queryRunner.query(
      `CREATE TABLE "stock1m" (
        "id" SERIAL, 
        "datetime" TIMESTAMP NOT NULL, 
        "ticker" character varying(12) NOT NULL, 
        "open" numeric(10,2) NOT NULL, 
        "high" numeric(10,2) NOT NULL, 
        "low" numeric(10,2) NOT NULL, 
        "close" numeric(10,2) NOT NULL, 
        "volume" bigint NOT NULL, 
        CONSTRAINT "stock1m_unique" UNIQUE ("ticker", "datetime"), 
        CONSTRAINT "PK_2b96791ee74ead388b05c1d2c5e" PRIMARY KEY ("id", "datetime")
      ) PARTITION BY RANGE (datetime)`,
    );
    await queryRunner.query(
      `CREATE INDEX "idx_stock1m_ticker_datetime" ON "stock1m" ("ticker", "datetime") `,
    );
    await queryRunner.query(
      `CREATE INDEX "idx_stock1m_datetime" ON "stock1m" ("datetime") `,
    );
    await queryRunner.query(
      `CREATE TABLE "stock1h" (
        "id" SERIAL, 
        "datetime" TIMESTAMP NOT NULL, 
        "ticker" character varying(12) NOT NULL, 
        "open" numeric(10,2) NOT NULL, 
        "high" numeric(10,2) NOT NULL, 
        "low" numeric(10,2) NOT NULL, 
        "close" numeric(10,2) NOT NULL, 
        "volume" bigint NOT NULL, 
        CONSTRAINT "stock1h_unique" UNIQUE ("ticker", "datetime"), 
        CONSTRAINT "PK_54cfd8c94ecf888c314366e666a" PRIMARY KEY ("id", "datetime")
      ) PARTITION BY RANGE (datetime)`,
    );
    await queryRunner.query(
      `CREATE INDEX "idx_stock1h_ticker_datetime" ON "stock1h" ("ticker", "datetime") `,
    );
    await queryRunner.query(
      `CREATE INDEX "idx_stock1h_datetime" ON "stock1h" ("datetime") `,
    );
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`DROP INDEX "public"."idx_stock1h_datetime"`);
    await queryRunner.query(
      `DROP INDEX "public"."idx_stock1h_ticker_datetime"`,
    );
    await queryRunner.query(`DROP TABLE "stock1h"`);
    await queryRunner.query(`DROP INDEX "public"."idx_stock1m_datetime"`);
    await queryRunner.query(
      `DROP INDEX "public"."idx_stock1m_ticker_datetime"`,
    );
    await queryRunner.query(`DROP TABLE "stock1m"`);
    await queryRunner.query(`DROP INDEX "public"."idx_stock1d_datetime"`);
    await queryRunner.query(
      `DROP INDEX "public"."idx_stock1d_ticker_datetime"`,
    );
    await queryRunner.query(`DROP TABLE "stock1d"`);
  }
}
