Importing LDS data
------------------

Use scripts/load_lds_dataset.sh to load data initially, similar to the other load scripts.

Arguments are "load_lds_dataset.sh {initial|update} <database> <layer_id> <layer_name> [<viewparams> [<filter>]]"

use "initial" as the first argument
<database> is the database of the dataset you wish to import to
<layer_id> is the numeric ID from lds, e.g. 787 is layer v:x787.
<layer_name> is the table name of the layer you wish to import
<viewparams> is the date range you wish to import, in the form from:YYYY-MM-DD;to:YYYY-MM-DD.
Use 1970-01-01 as the from date and the date of YESTERDAY UTC as the to date. E.g. at 9am on 8 Nov 2012 NZDT, use 2012-11-06 as the date.
<filter> is a CQL filter for the data. You cannot change this later.

When you set up the layer, make sure to set wfs_type_name to the layer_id (e.g. 787, not v:x787) and wfs_cql_filter to the EXACT filter you
used in the import script. Also set the update type to "LINZ Data Service".

All layers in your dataset must have the same version, and will be updated together, so be sure to use the same 'to date' when you import them. Also make
sure this date is set as the initial version for the dataset.

You can update the dataset using the link in the admin section for the dataset.
