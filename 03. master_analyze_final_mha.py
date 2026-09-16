"""
MASTER ANALYSIS FINAL (SAFE MODE): Membaca file .mha yang sudah selesai
Script ini aman dijalankan meskipun simulasi belum 100% selesai.
"""
import SimpleITK as sitk
import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\simulasi_imrt2\02_voxelized")

PHANTOMS = [
    'newborn_male', 'newborn_female',
    '1y_male', '1y_female',
    '5y_male', '5y_female',
    '10y_male', '10y_female',
    '15y_male', '15y_female'
]

ORGANS = ["Brain", "EyeLenses_Left", "EyeLenses_Right"]

print("="*80)
print("MULAI MASTER ANALYSIS FINAL (Safe Mode)")
print("="*80)

all_results = []

for phantom in PHANTOMS:
    print(f"\n Memproses Phantom: {phantom}")
    phantom_dir = BASE_DIR / phantom
    
    brain_nii = phantom_dir / "Brain.nii"
    if not brain_nii.exists():
        print(f"  ⚠️ Folder atau Brain.nii tidak ditemukan. Melewati...")
        continue
        
    brain_ref_img = sitk.ReadImage(str(brain_nii))
    
    # Cek ketersediaan file dosis
    dose_files = {
        '0mm': phantom_dir / "dose_posterior_fossa_0mm_edep.mha",
        'plus2mm': phantom_dir / "dose_posterior_fossa_plus2mm_edep.mha",
        'minus2mm': phantom_dir / "dose_posterior_fossa_minus2mm_edep.mha"
    }
    
    # Jika salah satu file dosis belum ada, lewati phantom ini untuk sementara
    if not all(f.exists() and f.stat().st_size > 10000 for f in dose_files.values()):
        print(f"  ⏳ Simulasi untuk {phantom} belum lengkap. Melewati untuk saat ini...")
        continue
    
    print(f"  📂 Membaca 3 file dosis...")
    dose_0_img = sitk.ReadImage(str(dose_files['0mm']))
    dose_p2_img = sitk.ReadImage(str(dose_files['plus2mm']))
    dose_m2_img = sitk.ReadImage(str(dose_files['minus2mm']))
    
    dose_0_img.CopyInformation(brain_ref_img)
    dose_p2_img.CopyInformation(brain_ref_img)
    dose_m2_img.CopyInformation(brain_ref_img)
    
    d0_arr = sitk.GetArrayFromImage(dose_0_img)
    dp2_arr = sitk.GetArrayFromImage(dose_p2_img)
    dm2_arr = sitk.GetArrayFromImage(dose_m2_img)
    
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(brain_ref_img)
    resampler.SetInterpolator(sitk.sitkNearestNeighbor)
    
    for organ in ORGANS:
        mask_path = phantom_dir / f"{organ}.nii"
        if not mask_path.exists():
            continue
            
        mask_img = sitk.ReadImage(str(mask_path))
        resampled_mask_img = resampler.Execute(mask_img)
        mask_arr = sitk.GetArrayFromImage(resampled_mask_img)
        
        v0 = d0_arr[mask_arr > 0]
        vp2 = dp2_arr[mask_arr > 0]
        vm2 = dm2_arr[mask_arr > 0]
        
        if len(v0) == 0:
            continue
            
        total_vol_cm3 = len(v0) * 0.001
        
        d0_mean, d0_max = np.mean(v0), np.max(v0)
        dp2_mean, dp2_max = np.mean(vp2), np.max(vp2)
        dm2_mean, dm2_max = np.mean(vm2), np.max(vm2)
        
        epsilon = 1e-9
        delta_p2_mean = ((dp2_mean - d0_mean) / (d0_mean + epsilon)) * 100
        delta_p2_max = ((dp2_max - d0_max) / (d0_max + epsilon)) * 100
        delta_m2_mean = ((dm2_mean - d0_mean) / (d0_mean + epsilon)) * 100
        delta_m2_max = ((dm2_max - d0_max) / (d0_max + epsilon)) * 100
        
        def get_d_percentile(vals, pct):
            return np.percentile(vals, 100 - pct) if len(vals) > 0 else 0.0
            
        d0_d2 = get_d_percentile(v0, 2)
        dp2_d2 = get_d_percentile(vp2, 2)
        dm2_d2 = get_d_percentile(vm2, 2)
        
        v5gy_0 = np.sum(v0 >= 5.0) * 0.001
        v5gy_p2 = np.sum(vp2 >= 5.0) * 0.001
        v5gy_m2 = np.sum(vm2 >= 5.0) * 0.001
        
        threshold_infield = 0.5 * d0_max 
        vol_infield_0 = np.sum(v0 >= threshold_infield) * 0.001
        vol_infield_p2 = np.sum(vp2 >= threshold_infield) * 0.001
        vol_infield_m2 = np.sum(vm2 >= threshold_infield) * 0.001
        
        transition_p2 = max(0, vol_infield_0 - vol_infield_p2)
        transition_m2 = max(0, vol_infield_0 - vol_infield_m2)
        
        asymmetry_mean = abs(delta_p2_mean) - abs(delta_m2_mean)
        asymmetry_max = abs(delta_p2_max) - abs(delta_m2_max)

        age_str = phantom.split('_')[0] 
        sex = phantom.split('_')[1]     
        
        all_results.append({
            "Phantom_ID": phantom,
            "Age_Group": age_str,
            "Sex": sex,
            "Organ": organ,
            "Volume_Total_cm3": round(total_vol_cm3, 3),
            "Delta_D_mean_+2mm_%": round(delta_p2_mean, 2),
            "Delta_D_mean_-2mm_%": round(delta_m2_mean, 2),
            "Delta_D_max_+2mm_%": round(delta_p2_max, 2),
            "Delta_D_max_-2mm_%": round(delta_m2_max, 2),
            "D0_D2percent_Gy": round(d0_d2, 4),
            "D+2_D2percent_Gy": round(dp2_d2, 4),
            "D-2_D2percent_Gy": round(dm2_d2, 4),
            "V5Gy_0mm_cm3": round(v5gy_0, 4),
            "V5Gy_+2mm_cm3": round(v5gy_p2, 4),
            "V5Gy_-2mm_cm3": round(v5gy_m2, 4),
            "Vol_InField_0mm_cm3": round(vol_infield_0, 4),
            "Vol_InField_+2mm_cm3": round(vol_infield_p2, 4),
            "Vol_InField_-2mm_cm3": round(vol_infield_m2, 4),
            "Transition_Out_+2mm_cm3": round(transition_p2, 4),
            "Transition_Out_-2mm_cm3": round(transition_m2, 4),
            "Asymmetry_DeltaMean_%": round(asymmetry_mean, 2),
            "Asymmetry_DeltaMax_%": round(asymmetry_max, 2)
        })
        
    print(f"  ✅ {phantom} selesai dianalisis.")

if len(all_results) > 0:
    df_master = pd.DataFrame(all_results)
    output_csv = BASE_DIR / "MASTER_RESULTS_FINAL_PAPER.csv"
    df_master.to_csv(output_csv, index=False)

    print("\n" + "="*80)
    print(f"🎉 ANALISIS SELESAI! ({len(all_results)} baris data berhasil diekstrak)")
    print(f"Data tersimpan di: {output_csv}")
    print("="*80)
    print("\nPreview Data:")
    print(df_master.to_string(index=False))
else:
    print("\n⚠️ Belum ada data yang lengkap untuk dianalisis. Biarkan simulasi berjalan.")