import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize, timeout } from 'rxjs';
import { Analisis, SolicitudesService } from './solicitudes.service';

@Component({
  selector: 'app-solicitudes',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './solicitudes.component.html',
  styleUrl: './solicitudes.component.css',
})
export class SolicitudesComponent {
  private readonly service = inject(SolicitudesService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  readonly loading = signal(false);
  readonly error = signal('');
  readonly resultado = signal<Analisis | null>(null);
  readonly form = this.fb.nonNullable.group({
    id: ['', [Validators.required, Validators.maxLength(100), Validators.pattern(/^[\p{L}\p{N}_-]+$/u)]],
    cliente_id: ['', [Validators.required, Validators.maxLength(100), Validators.pattern(/^[\p{L}\p{N}_-]+$/u)]],
    texto: ['', [Validators.required, Validators.maxLength(20000)]],
  });

  analizar(): void {
    if (this.loading()) return;
    const values = this.form.getRawValue();
    this.form.setValue({
      id: values.id.trim(), cliente_id: values.cliente_id.trim(), texto: values.texto.trim(),
    });
    this.error.set('');
    this.resultado.set(null);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.error.set('Completa los campos: identificadores de hasta 100 letras, números, guiones o guiones bajos y texto de hasta 20.000 caracteres.');
      return;
    }
    this.loading.set(true);
    this.service.analizar(this.form.getRawValue()).pipe(
      timeout(40000),
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.loading.set(false)),
    ).subscribe({
      next: (analisis) => this.resultado.set(analisis),
      error: (err: unknown) => {
        const status = err instanceof HttpErrorResponse ? err.status : undefined;
        const messages: Record<number, string> = {
          0: 'No se pudo conectar con la API. Comprueba la conexión.',
          401: 'Debes iniciar sesión de nuevo.',
          403: 'No tienes permiso para analizar solicitudes.',
          409: 'Este ID ya tiene un análisis guardado. Usa otro para una nueva solicitud.',
          422: 'La API rechazó los datos. Revisa los campos.',
          502: 'No se pudo completar el análisis.',
          503: 'El almacenamiento no está disponible temporalmente.',
        };
        this.error.set(status === undefined
          ? 'La petición no terminó a tiempo. Consulta el ID antes de reenviarla: podría haberse guardado.'
          : messages[status] ?? 'Ocurrió un error al analizar la solicitud.');
      },
    });
  }
}
