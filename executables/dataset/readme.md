Preparing the publicly available datasets
=========================================

Below we detail the instructions to use the two publicly available browser
fingerprint datasets.


## FPStalker

The FPStalker dataset is available on the
[FPStalker github repository](https://github.com/Spirals-Team/FPStalker).

1. Download the two archives
   [extension1.txt.tar.gz](https://github.com/Spirals-Team/FPStalker/raw/master/extension1.txt.tar.gz)
   and
   [extension2.txt.tar.gz](https://github.com/Spirals-Team/FPStalker/raw/master/extension2.txt.tar.gz).
2. Extract the two archives and regroup them in a file named
   `tableFingerprints.sql`:
  ```sh
  tar zxvf extension1.txt.tar.gz
  tar zxvf extension2.txt.tar.gz
  cat extension1.txt extension2.txt > tableFingerprints.sql
  ```
3. Prepare the FPStalker dataset using the dedicated preprocessing script:
  ```sh
  python -m executables.dataset.preprocess_fpstalker sql_script_path output_directory
  ```
  - The `sql_script_path` is the path to the `tableFingerprints.sql` file
    (which is required to have this name).
  - The `output_directory` is the directory where to save the resulting data.
  - You can specify the `--keep-raw-canvas` option to hold the complete base64
    encoded canvas images in the fingerprint dataset.
4. The resulting browser fingerprint dataset is in `output_directory`:
  - The fingerprint dataset is saved in `fingerprints.csv`.
  - The canvases are extracted as images in the `canvas` directory with a
    subdirectory named after the type of canvas and each image is named after
    its hash value in the fingerprint dataset.


## HTillmann

The HTillmann dataset is available on the
[blog of Henning Tillmann](https://www.henning-tillmann.de/2013/10/browser-fingerprinting-93-der-nutzer-hinterlassen-eindeutige-spuren).

1. Download the file named
   [MySQL-Tabelle “bfp”](http://bfp.henning-tillmann.de/downloads/bfp.sql.zip).
2. Extract the archive as a file named `bfp.sql`:
  ```sh
  unzip bfp.sql.zip
  ```
3. Prepare the HTillmann dataset using the dedicated preprocessing script:
  ```sh
  python -m executables.dataset.preprocess_htillmann sql_script_path output_directory
  ```
  - The `sql_script_path` is the path to the `bfp.sql` file (which is required
    to have this name).
  - The `output_directory` is the directory where to save the resulting data.
4. The resulting browser fingerprint dataset is saved in
   `output_directory/fingerprints.csv`.
