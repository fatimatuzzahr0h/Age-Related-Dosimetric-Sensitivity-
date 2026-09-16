"""
MASTER SIMULATION FINAL: Menggunakan format .mha untuk menghindari bug Windows
Menjalankan 10 Phantom x 3 Kondisi = 30 Simulasi
"""
import opengate as gate
import SimpleITK as sitk
import time
from pathlib import Path

BASE_DIR = Path(r"C:\simulasi_imrt2\02_voxelized")

PHANTOMS = [
    'newborn_male', 'newborn_female',
    '1y_male', '1y_female',
    '5y_male', '5y_female',
    '10y_male', '10y_female',
    '15y_male', '15y_female'
]

SHIFTS = {
    '0mm': 0.0,
    'plus2mm': 0.2,   
    'minus2mm': -0.2  
}

def run_single_simulation(phantom_id, shift_name, shift_cm):
    # Cek apakah file sudah ada
    output_file = BASE_DIR / phantom_id / f"dose_posterior_fossa_{shift_name}_edep.mha"
    if output_file.exists() and output_file.stat().st_size > 10000:
        print(f"⏭️ SKIP: {phantom_id} | {shift_name} (File valid sudah ada)")
        return

    print(f"\n{'='*70}")
    print(f"MULAI: {phantom_id} | Shift: {shift_name}")
    print(f"{'='*70}")
    
    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = 1 
    sim.output_dir = str(BASE_DIR / phantom_id)
    
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.enable_decay = False

    world = sim.world
    world.size = [60 * gate.g4_units.cm, 60 * gate.g4_units.cm, 60 * gate.g4_units.cm]
    world.material = "G4_AIR"

    brain_nii_path = str(BASE_DIR / phantom_id / "Brain.nii")
    phantom = sim.add_volume("Image", "brain_phantom")
    phantom.image = brain_nii_path
    phantom.material = "G4_WATER" 
    phantom.translation = [shift_cm * gate.g4_units.cm, 0, 0] 

    isocenter = [0, -2 * gate.g4_units.cm, -2 * gate.g4_units.cm] 
    energy = 6 * gate.g4_units.MeV
    n_particles = 5e6 

    source_left = sim.add_source("GenericSource", "beam_left")
    source_left.particle = "gamma"
    source_left.energy.type = "mono"
    source_left.energy.mono = energy
    source_left.position.type = "disc"
    source_left.position.radius = 5 * gate.g4_units.cm
    source_left.position.translation = [-40 * gate.g4_units.cm, 0, 0] 
    source_left.direction.type = "focused"
    source_left.direction.focus_point = isocenter 
    source_left.n = n_particles

    source_right = sim.add_source("GenericSource", "beam_right")
    source_right.particle = "gamma"
    source_right.energy.type = "mono"
    source_right.energy.mono = energy
    source_right.position.type = "disc"
    source_right.position.radius = 5 * gate.g4_units.cm
    source_right.position.translation = [40 * gate.g4_units.cm, 0, 0] 
    source_right.direction.type = "focused"
    source_right.direction.focus_point = isocenter 
    source_right.n = n_particles

    # --- KONFIGURASI KRITIS YANG SUDAH TERBUKTI ---
    dose_actor = sim.add_actor("DoseActor", "dose")
    dose_actor.attached_to = "brain_phantom" 
    
    # Format .mha (Single File)
    dose_actor.output_filename = f"dose_posterior_fossa_{shift_name}.mha" 
    dose_actor.write_to_disk = True
    dose_actor.hit_type = "random"
    
    # Paksa Grid Eksplisit dari NIfTI
    img_sitk = sitk.ReadImage(brain_nii_path)
    dose_actor.size = list(img_sitk.GetSize()) 
    dose_actor.spacing = [s * gate.g4_units.mm for s in img_sitk.GetSpacing()]
    # ------------------------------------------------

    start_time = time.time()
    sim.run(start_new_process=True) 
    end_time = time.time()
    
    if output_file.exists() and output_file.stat().st_size > 10000:
        size_mb = output_file.stat().st_size / 1e6
        print(f"✅ SELESAI: {phantom_id} | {shift_name} (Waktu: {(end_time - start_time)/60:.1f} mnt, Ukuran: {size_mb:.2f} MB)")
    else:
        print(f" GAGAL: File output kosong untuk {phantom_id} | {shift_name}")

if __name__ == '__main__':
    print("🚀 MEMULAI MASTER SIMULATION FINAL (Format .mha)")
    print("⚠️  PERINGATAN: Proses ini akan memakan waktu 15-20 jam. Jangan matikan laptop!")

    for phantom in PHANTOMS:
        for shift_name, shift_cm in SHIFTS.items():
            run_single_simulation(phantom, shift_name, shift_cm)

    print("\n" + "="*70)
    print("🎉 SEMUA 30 SIMULASI SELESAI! 🎉")
    print("="*70)