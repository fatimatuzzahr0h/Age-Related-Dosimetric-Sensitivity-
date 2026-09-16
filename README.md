Supplementary Material
Title: Age-Related Dosimetric Sensitivity to ±2 mm X-Axis Setup Displacement in Pediatric Cranial Radiotherapy: A Monte Carlo Study Using ICRP-156 Computational Phantoms
Document Type: Supplementary Source Code and Computational Pipeline

S1. Software Environment and Dependencies
The complete computational pipeline was developed in Python (version 3.11). The Monte Carlo radiation transport simulations were executed using the OpenGATE toolkit (version 10.1.1), which is built upon the Geant4 toolkit (version 11.04). Post-processing, volumetric data extraction, and statistical analyses were performed using the following standard scientific libraries: SimpleITK, NumPy, Pandas, SciPy, PyVista, Trimesh, and Nibabel.

S2. Script S1: Phantom Voxelization and Preparation
This script converts the mesh-type ICRP-156 pediatric phantoms into isotropic 1×1×1 mm³ voxelized representations. It utilizes a binary hole-filling algorithm to ensure the anatomical structures (e.g., Brain, Eye Lenses) are solid volumes, which is a prerequisite for accurate Monte Carlo particle navigation.

S3. Script S2: Batch Monte Carlo Simulation
This script automates the execution of 30 Monte Carlo simulations (10 phantoms × 3 lateral shift conditions). It configures the OpenGATE DoseActor to export 3D dose distributions in the MetaImage All-in-One (.mha) format, ensuring robust volumetric data storage.

S4. Script S3: Volumetric Data Extraction
This script processes the generated (.mha) dose files. It resamples the dose grids to the anatomical masks of the Brain and Eye Lenses, calculating relative dose variations (ΔD%), dose-volume metrics, in-field/out-of-field transitions, and directional asymmetry.

S5. Script S4: Data Imputation for Out-of-Grid Organs
For older phantoms (10y and 15y females), the eye lenses resided outside the primary brain dose calculation grid. This script applies a mask-reference resampling technique to accurately extract the zero-dose values, confirming the "protective effect" of anatomical growth.
S6. Script S5: Statistical Analysis Pipeline
This script performs the non-parametric statistical evaluations (Wilcoxon Signed-Rank Test and Spearman Rank Correlation) to assess the significance of the dosimetric variations and age-dependent trends.
