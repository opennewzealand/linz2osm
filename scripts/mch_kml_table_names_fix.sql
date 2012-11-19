\t
select 'UPDATE geometry_columns SET f_table_name = ''' || 'mch_memorial_' || replace(f_table_name, ' ', '_') || ''' WHERE f_table_name = ''' || f_table_name || ''';' from geometry_columns ;
select 'ALTER INDEX "' || f_table_name || '_geom_idx" RENAME TO mch_memorial_' || replace(f_table_name, ' ', '_') || '_geom_idx;' from geometry_columns ;
select 'ALTER INDEX "' || f_table_name || '_pk" RENAME TO mch_memorial_' || replace(f_table_name, ' ', '_') || '_pk;' from geometry_columns ;
select 'ALTER SEQUENCE "' || f_table_name || '_ogc_fid_seq" RENAME TO mch_memorial_' || replace(f_table_name, ' ', '_') || '_ogc_fid_seq;' from geometry_columns ;
select 'ALTER TABLE "' || f_table_name || '" RENAME TO mch_memorial_' || replace(f_table_name, ' ', '_') || ';' from geometry_columns ;
