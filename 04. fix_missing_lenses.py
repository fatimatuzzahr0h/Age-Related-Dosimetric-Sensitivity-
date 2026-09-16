"""
FIX MISSING DATA: Menambahkan data Lensa Mata yang hilang (10y M/F, 15y F)
Menggunakan teknik Mask-Reference Resampling untuk mengekstrak dosis secara akurat.
"""
import pandas as pd
import SimpleITK as sitk
import numpy as np
from pathlib import Path

BASE_DIR = Path(r"C:\simulasi_imrt2\02_voxelized")
CSV_PATH = BASE_DIR / "MASTER_RESULTS_FINAL_PAPER.csv"

# 1. Muat data yang sudah ada
df = pd.read_csv(CSV_PATH)

# 2. Identifikasi yang kurang (Berdasarkan CSV Anda)
missing_phantoms = ['10y_male', '10y_female', '15y_female']
organs_to_fix = ['EyeLenses_Left', 'EyeLenses_Right']

print("="*70)
print("MENCARI DAN MEMPERBAIKI DATA YANG HILANG...")
print("="*70)

new_rows = []

for phantom in missing_phantoms:
    print(f"\n Memproses: {phantom}")
    phantom_dir = BASE_DIR / phantom
    
    # Baca file dosis (.mha)
    dose_0_img = sitk.ReadImage(str(phantom_dir / "dose_posterior_fossa_0mm_edep.mha"))
    dose_p2_img = sitk.ReadImage(str(phantom_dir / "dose_posterior_fossa_plus2mm_edep.mha"))
    dose_m2_img = sitk.ReadImage(str(phantom_dir / "dose_posterior_fossa_minus2mm_edep.mha"))
    
    # Setup Resampler: Gunakan INTERPOLASI LINEAR untuk dosis (lebih akurat daripada nearest neighbor)
    resampler = sitk.ResampleImageFilter()
    resampler.SetInterpolator(sitk.sitkLinear) 
    
    for organ in organs_to_fix:
        mask_path = phantom_dir / f"{organ}.nii"
        if not mask_path.exists():
            continue
            
        mask_img = sitk.ReadImage(str(mask_path))
        
        # --- TRIK KRITIS: Jadikan Mask Organ sebagai REFERENSI GRID ---
        resampler.SetReferenceImage(mask_img)
        
        # Resample peta dosis ke dalam grid organ
        d0_resampled = sitk.GetArrayFromImage(resampler.Execute(dose_0_img))
        dp2_resampled = sitk.GetArrayFromImage(resampler.Execute(dose_p2_img))
        dm2_resampled = sitk.GetArrayFromImage(resampler.Execute(dose_m2_img))
        
        mask_arr = sitk.GetArrayFromImage(mask_img)
        
        # Ekstrak nilai dosis di mana mask > 0
        v0 = d0_resampled[mask_arr > 0]
        vp2 = dp2_resampled[mask_arr > 0]
        vm2 = dm2_resampled[mask_arr > 0]
        
        if len(v0) == 0:
            print(f"  ⚠️ {organ} benar-benar di luar grid dosis (Dosis = 0).")
            continue
            
        total_vol_cm3 = len(v0) * 0.001
        
        # Hitung Metrik
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
        
        # Buat baris data baru
        new_row = {
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
        }
        new_rows.append(new_row)
        print(f"  ✅ {organ} berhasil diekstrak! (Vol: {total_vol_cm3} cm³, D0_mean: {d0_mean:.6f} Gy)")

# 3. Gabungkan dengan DataFrame lama dan Simpan
if new_rows:
    df_new = pd.DataFrame(new_rows)
    df_final = pd.concat([df, df_new], ignore_index=True)
    df_final.to_csv(CSV_PATH, index=False)
    
    print("\n" + "="*70)
    print(f"🎉 SUKSES! {len(new_rows)} baris data telah ditambahkan.")
    print(f"File CSV final sekarang memiliki {len(df_final)} baris data lengkap!")
    print("="*70)
else:
    print("\n⚠️ Tidak ada data baru yang bisa diekstrak. Organ mungkin benar-benar di luar grid dosis simulasi.")