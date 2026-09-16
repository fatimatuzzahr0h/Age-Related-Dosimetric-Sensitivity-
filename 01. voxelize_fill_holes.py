"""
MASTER VOXELIZATION v2: Dengan Binary Fill Holes
Mengisi bagian dalam mesh yang berongga (hollow)
"""
import pyvista as pv
import trimesh
import numpy as np
import nibabel as nib
from pathlib import Path
import pandas as pd
from scipy import ndimage

# Konfigurasi
VOXEL_SIZE_MM = 1.0
INPUT_DIR = Path(r"C:\simulasi_imrt2\01_mesh_files")
OUTPUT_DIR = Path(r"C:\simulasi_imrt2\02_voxelized")
LOG_DIR = Path(r"C:\simulasi_imrt2\05_documentation")

PHANTOM_FOLDERS = {
    'newborn_male':   'newborn_male',
    'newborn_female': 'newborn_female',
    '1y_male':        '1y_male',
    '1y_female':      '1y_female',
    '5y_male':        '5y_male',
    '5y_female':      '5y_female',
    '10y_male':       '10y_male',
    '10y_female':     '10y_female',
    '15y_male':       '15y_male',
    '15y_female':     '15y_female',
}

ORGANS = {
    'Brain':          ['brain'],
    'Thyroid':        ['thyroid', 'tyroid'],
    'EyeLenses_Left': ['eyelens_l', 'lens_l'],
    'EyeLenses_Right':['eyelens_r', 'lens_r'],
}

def find_mesh_file(folder_path, organ_keywords):
    for stl_file in folder_path.glob("*.stl"):
        name_lower = stl_file.stem.lower()
        for kw in organ_keywords:
            if kw in name_lower:
                return stl_file
    return None

def voxelize_and_fill(mesh, voxel_size_mm):
    """
    1. Konversi cm -> mm
    2. Voxelisasi (menangkap cangkang)
    3. Isi lubang (fill holes) untuk membuat solid
    """
    # STEP 1: Konversi Unit (cm -> mm)
    mesh.points *= 10.0
    
    # STEP 2: Persiapan untuk Trimesh
    vertices = mesh.points
    faces = mesh.faces.reshape(-1, 4)[:, 1:]
    tri_mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    
    # STEP 3: Voxelisasi Awal (Akan menangkap cangkang/permukaan)
    print(f"      -> Voxelizing surface...")
    voxel_grid = tri_mesh.voxelized(pitch=voxel_size_mm)
    binary_array = voxel_grid.matrix.astype(np.uint8)
    
    # STEP 4: ISI LUBANG (FILL HOLES) - INI KUNCINYA!
    # Mengisi semua voxel yang terkurung di dalam cangkang
    print(f"      -> Filling internal holes (making solid)...")
    filled_array = ndimage.binary_fill_holes(binary_array).astype(np.uint8)
    
    # Dapatkan origin
    bounds = tri_mesh.bounds
    origin = bounds[0]
    
    return filled_array, origin

def save_as_nifti(array, origin, spacing, output_path):
    affine = np.eye(4)
    affine[0, 3] = origin[0]
    affine[1, 3] = origin[1]
    affine[2, 3] = origin[2]
    affine[0, 0] = spacing
    affine[1, 1] = spacing
    affine[2, 2] = spacing
    
    img = nib.Nifti1Image(array, affine)
    nib.save(img, output_path)

def main():
    print("="*80)
    print("MASTER VOXELIZATION v2: Fill Holes Method")
    print("="*80)
    
    volume_log = []
    
    for phantom_id, folder_name in PHANTOM_FOLDERS.items():
        print(f"\n{'='*80}")
        print(f"Phantom: {phantom_id}")
        print(f"{'='*80}")
        
        folder_path = INPUT_DIR / folder_name
        if not folder_path.exists():
            print(f"  ✗ Folder tidak ditemukan")
            continue
        
        output_phantom_dir = OUTPUT_DIR / phantom_id
        output_phantom_dir.mkdir(parents=True, exist_ok=True)
        
        for organ_name, keywords in ORGANS.items():
            print(f"\n  Organ: {organ_name}")
            
            mesh_file = find_mesh_file(folder_path, keywords)
            if mesh_file is None:
                print(f"    ✗ File tidak ditemukan")
                continue
            
            print(f"    File: {mesh_file.name}")
            
            try:
                mesh = pv.read(str(mesh_file))
                
                # Hitung volume analitik (seharusnya ~380 cm³ untuk brain)
                # PyVista volume dalam unit³ (cm³ karena file asli cm)
                # Setelah di-scale 10x, volume jadi 1000x
                vol_analytical_cm3 = (mesh.volume * 1000) / 1000.0 # *1000 karena scale^3, /1000 untuk mm³->cm³
                # Koreksi: mesh.volume sebelum scale adalah cm³. Setelah scale 10x, jadi mm³.
                # Jadi volume_mm3 = mesh.volume * 1000. Volume_cm3 = mesh.volume.
                # TAPI, mesh.volume di PyVista bisa negatif jika normals terbalik.
                vol_analytical_cm3 = abs(mesh.volume) # Ini dalam cm³ (karena file asli cm)
                print(f"    Analytical Volume (Reference): {vol_analytical_cm3:.2f} cm³")
                
                # Voxelisasi & Fill
                voxel_array, origin = voxelize_and_fill(mesh, VOXEL_SIZE_MM)
                
                # Hitung volume hasil
                voxel_count = np.sum(voxel_array > 0)
                volume_mm3 = voxel_count * (VOXEL_SIZE_MM ** 3)
                volume_cm3 = volume_mm3 / 1000.0
                
                print(f"    ✓ Voxel count: {voxel_count}")
                print(f"    ✓ Final Volume: {volume_cm3:.2f} cm³")
                
                # Bandingkan dengan analitik
                if organ_name == 'Brain':
                    if 300 <= volume_cm3 <= 450:
                        print(f"    ✓✓✓ BRAIN VOLUME NORMAL! (~380 cm³)")
                    else:
                        print(f"    ⚠ Brain volume masih aneh")
                
                # Simpan
                output_nii = output_phantom_dir / f"{organ_name}.nii"
                save_as_nifti(voxel_array, origin, VOXEL_SIZE_MM, output_nii)
                print(f"    ✓ Saved: {output_nii.name}")
                
                volume_log.append({
                    'phantom_id': phantom_id,
                    'organ': organ_name,
                    'volume_cm3': volume_cm3,
                    'voxel_count': int(voxel_count),
                    'file': mesh_file.name
                })
                
            except Exception as e:
                print(f"    ✗ Error: {e}")
                import traceback
                traceback.print_exc()
    
    # Simpan Log
    df = pd.DataFrame(volume_log)
    log_file = LOG_DIR / "voxelization_v2_log.csv"
    df.to_csv(log_file, index=False)
    
    print(f"\n{'='*80}")
    print("SELESAI! Log tersimpan di: {log_file}")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()