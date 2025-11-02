import math
import tkinter as tk
from tkinter import ttk, messagebox


class ForwardVolApp(tk.Tk):
    """A small GUI app to compute forward (implied) volatility
    between two expiries from their DTEs and IVs.

    Forward variance identity:
        sigma_fwd = sqrt( (sigma2^2 * T2 - sigma1^2 * T1) / (T2 - T1) )

    with T = DTE / 365 and sigma = IV / 100 (annualized).

    Forward Factor:
        FF = (FrontMonthIV − ForwardIV(1→2)) / ForwardIV(1→2)
           = (σ1 − σ_fwd) / σ_fwd
    """

    def __init__(self):
        super().__init__()
        self.title("Forward Volatility Calculator")
        self.geometry("840x620")
        self.resizable(False, False)
        self._build_ui()

    # ------------------------------ UI ------------------------------ #
    def _build_ui(self):
        main = ttk.Frame(self, padding=16)
        main.grid(row=0, column=0, sticky="nsew")

        title = ttk.Label(
            main,
            text="Forward Volatility Calculator",
            font=("Segoe UI", 16, "bold"),
        )
        title.grid(row=0, column=0, columnspan=3, sticky="w")

        formula_text = (
            "Formula\n"
            "\n"
            "  σ_fwd = sqrt( (σ₂²·T₂ − σ₁²·T₁) / (T₂ − T₁) )\n"
            "  FF = (σ₁ − σ_fwd) / σ_fwd\n"
            "\n"
            "Definitions\n"
            "  T = DTE / 365\n"
            "  σ = IV / 100  (IV entered as a percent, e.g., 24.5 = 24.5%)\n"
        )

        formula = ttk.Label(
            main,
            text=formula_text,
            justify="left",
            font=("Segoe UI", 10),
        )
        formula.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 16))

        # Inputs
        inputs = ttk.LabelFrame(main, text="Inputs", padding=12)
        inputs.grid(row=2, column=0, sticky="nsew")

        self.dte1_var = tk.StringVar()
        self.iv1_var = tk.StringVar()
        self.dte2_var = tk.StringVar()
        self.iv2_var = tk.StringVar()

        ttk.Label(inputs, text="DTE₁ (days)").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        dte1_entry = ttk.Entry(inputs, width=12, textvariable=self.dte1_var)
        dte1_entry.grid(row=0, column=1, sticky="w", pady=4)

        ttk.Label(inputs, text="IV₁ (%)").grid(row=0, column=2, sticky="w", padx=(16, 8), pady=4)
        iv1_entry = ttk.Entry(inputs, width=12, textvariable=self.iv1_var)
        iv1_entry.grid(row=0, column=3, sticky="w", pady=4)

        ttk.Label(inputs, text="DTE₂ (days)").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        dte2_entry = ttk.Entry(inputs, width=12, textvariable=self.dte2_var)
        dte2_entry.grid(row=1, column=1, sticky="w", pady=4)

        ttk.Label(inputs, text="IV₂ (%)").grid(row=1, column=2, sticky="w", padx=(16, 8), pady=4)
        iv2_entry = ttk.Entry(inputs, width=12, textvariable=self.iv2_var)
        iv2_entry.grid(row=1, column=3, sticky="w", pady=4)

        # Buttons
        btns = ttk.Frame(main)
        btns.grid(row=3, column=0, sticky="w", pady=(12, 0))

        calc_btn = ttk.Button(btns, text="Compute", command=self.compute)
        calc_btn.grid(row=0, column=0, padx=(0, 8))

        clear_btn = ttk.Button(btns, text="Clear", command=self.clear)
        clear_btn.grid(row=0, column=1)

        self.bind("<Return>", lambda _e: self.compute())

        # Outputs
        out = ttk.LabelFrame(main, text="Outputs", padding=12)
        out.grid(row=4, column=0, sticky="nsew", pady=(12, 0))

        # Left column: T and sigma
        ttk.Label(out, text="T₁ = DTE₁ / 365").grid(row=0, column=0, sticky="w")
        self.T1_val = ttk.Label(out, text="—")
        self.T1_val.grid(row=0, column=1, sticky="w", padx=(8, 24))

        ttk.Label(out, text="σ₁ = IV₁ / 100").grid(row=1, column=0, sticky="w")
        self.s1_val = ttk.Label(out, text="—")
        self.s1_val.grid(row=1, column=1, sticky="w", padx=(8, 24))

        ttk.Label(out, text="Total variance₁ = σ₁² · T₁").grid(row=2, column=0, sticky="w")
        self.tv1_val = ttk.Label(out, text="—")
        self.tv1_val.grid(row=2, column=1, sticky="w", padx=(8, 24))

        # Right column: T2, sigma2, total variance2
        ttk.Label(out, text="T₂ = DTE₂ / 365").grid(row=0, column=2, sticky="w")
        self.T2_val = ttk.Label(out, text="—")
        self.T2_val.grid(row=0, column=3, sticky="w", padx=(8, 24))

        ttk.Label(out, text="σ₂ = IV₂ / 100").grid(row=1, column=2, sticky="w")
        self.s2_val = ttk.Label(out, text="—")
        self.s2_val.grid(row=1, column=3, sticky="w", padx=(8, 24))

        ttk.Label(out, text="Total variance₂ = σ₂² · T₂").grid(row=2, column=2, sticky="w")
        self.tv2_val = ttk.Label(out, text="—")
        self.tv2_val.grid(row=2, column=3, sticky="w", padx=(8, 24))

        # Forward variance & vol (bottom row)
        sep = ttk.Separator(out, orient="horizontal")
        sep.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(8, 8))

        ttk.Label(out, text="Forward variance = (σ₂²·T₂ − σ₁²·T₁) / (T₂ − T₁)").grid(row=4, column=0, columnspan=2, sticky="w")
        self.fwd_var_val = ttk.Label(out, text="—")
        self.fwd_var_val.grid(row=4, column=2, columnspan=2, sticky="w", padx=(8, 0))

        ttk.Label(out, text="Forward volatility σ_fwd (annualized)").grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.fwd_vol_val = ttk.Label(out, text="—")
        self.fwd_vol_val.grid(row=5, column=2, columnspan=2, sticky="w", padx=(8, 0), pady=(6, 0))

        # Forward Factor
        ttk.Label(out, text="Forward Factor FF = (σ₁ − σ_fwd) / σ_fwd").grid(row=6, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.ff_ratio_val = ttk.Label(out, text="—")
        self.ff_ratio_val.grid(row=6, column=2, sticky="w", padx=(8, 0), pady=(6, 0))

        ttk.Label(out, text="FF (%)").grid(row=7, column=0, sticky="w")
        self.ff_pct_val = ttk.Label(out, text="—")
        self.ff_pct_val.grid(row=7, column=2, sticky="w", padx=(8, 0))

        note = ttk.Label(
            main,
            text=(
                "Notes: require DTE₂ > DTE₁ ≥ 0 and IVs ≥ 0. "
                "If forward variance is negative, the forward vol is not real (check inputs). "
                "If σ_fwd = 0, FF is undefined."
            ),
            foreground="#555",
            font=("Segoe UI", 9),
            wraplength=780,
            justify="left",
        )
        note.grid(row=5, column=0, sticky="w", pady=(10, 0))

    # --------------------------- Logic ------------------------------ #
    def _parse_inputs(self):
        try:
            dte1 = float(self.dte1_var.get())
            iv1 = float(self.iv1_var.get())
            dte2 = float(self.dte2_var.get())
            iv2 = float(self.iv2_var.get())
        except ValueError:
            raise ValueError("Please enter numeric values for all inputs.")

        if dte1 < 0 or dte2 < 0:
            raise ValueError("DTEs must be non-negative.")
        if dte2 <= dte1:
            raise ValueError("Require DTE₂ > DTE₁ so that T₂ > T₁.")
        if iv1 < 0 or iv2 < 0:
            raise ValueError("IVs must be non-negative (in percent).")

        return dte1, iv1, dte2, iv2

    def compute(self):
        try:
            dte1, iv1, dte2, iv2 = self._parse_inputs()
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e))
            return

        T1 = dte1 / 365.0
        T2 = dte2 / 365.0
        s1 = iv1 / 100.0
        s2 = iv2 / 100.0

        tv1 = (s1 ** 2) * T1
        tv2 = (s2 ** 2) * T2

        denom = T2 - T1
        if denom <= 0:
            messagebox.showerror("Invalid maturities", "T₂ must be greater than T₁.")
            return

        fwd_var = (tv2 - tv1) / denom
        if fwd_var < 0:
            # Show values we can, but warn about negative forward variance
            self.T1_val.config(text=f"{T1:.6f} yr")
            self.T2_val.config(text=f"{T2:.6f} yr")
            self.s1_val.config(text=f"{s1:.6f}")
            self.s2_val.config(text=f"{s2:.6f}")
            self.tv1_val.config(text=f"{tv1:.8f}")
            self.tv2_val.config(text=f"{tv2:.8f}")
            self.fwd_var_val.config(text=f"{fwd_var:.8f}  (negative)")
            self.fwd_vol_val.config(text="n/a (check inputs)")
            self.ff_ratio_val.config(text="n/a")
            self.ff_pct_val.config(text="n/a")
            messagebox.showwarning(
                "Negative forward variance",
                "Computed forward variance is negative. This implies the inputs are inconsistent with a real-valued forward volatility.",
            )
            return

        fwd_sigma = math.sqrt(fwd_var)  # annualized, in decimals

        # Forward Factor
        if fwd_sigma == 0.0:
            ff_ratio = None
        else:
            ff_ratio = (s1 - fwd_sigma) / fwd_sigma

        # Update UI
        self.T1_val.config(text=f"{T1:.6f} yr")
        self.T2_val.config(text=f"{T2:.6f} yr")
        self.s1_val.config(text=f"{s1:.6f}")
        self.s2_val.config(text=f"{s2:.6f}")
        self.tv1_val.config(text=f"{tv1:.8f}")
        self.tv2_val.config(text=f"{tv2:.8f}")
        self.fwd_var_val.config(text=f"{fwd_var:.8f}")
        self.fwd_vol_val.config(text=f"{fwd_sigma * 100:.4f} %")

        if ff_ratio is None:
            self.ff_ratio_val.config(text="undefined (σ_fwd = 0)")
            self.ff_pct_val.config(text="n/a")
        else:
            self.ff_ratio_val.config(text=f"{ff_ratio:.6f}")
            self.ff_pct_val.config(text=f"{ff_ratio * 100:.4f} %")

    def clear(self):
        for var in (self.dte1_var, self.iv1_var, self.dte2_var, self.iv2_var):
            var.set("")
        for lbl in (
            self.T1_val,
            self.T2_val,
            self.s1_val,
            self.s2_val,
            self.tv1_val,
            self.tv2_val,
            self.fwd_var_val,
            self.fwd_vol_val,
            self.ff_ratio_val,
            self.ff_pct_val,
        ):
            lbl.config(text="—")


if __name__ == "__main__":
    app = ForwardVolApp()
    app.mainloop()
