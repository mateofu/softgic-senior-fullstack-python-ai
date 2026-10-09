import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface Solicitud {
  id: string;
  texto: string;
  cliente_id: string;
}

export interface Analisis extends Solicitud {
  categoria: 'facturación' | 'técnico' | 'comercial' | 'otro';
  prioridad: 'alta' | 'media' | 'baja';
  respuesta: string;
  cliente: { id: string; nombre: string; plan: 'basico' | 'premium' } | null;
  tokens_entrada: number;
  tokens_salida: number;
  costo_estimado: string;
  uso_estimado: boolean;
}

@Injectable({ providedIn: 'root' })
export class SolicitudesService {
  private readonly http = inject(HttpClient);

  analizar(solicitud: Solicitud): Observable<Analisis> {
    return this.http.post<Analisis>('/solicitudes/analizar', solicitud);
  }
}
