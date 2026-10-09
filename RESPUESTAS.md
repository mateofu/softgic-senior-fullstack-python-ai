# Parte 5: preguntas de criterio

## 1. ¿Cuándo usaría n8n y cuándo LangGraph? Dé un ejemplo de cada uno.
Usaría n8n para integrar servicios con flujos visuales y reglas predecibles: clasificar un correo con IA, crear un ticket y notificar al equipo.
Elegiría LangGraph cuando necesito estado explícito, decisiones condicionales, ciclos y pruebas detalladas en código.
Ejemplo: un agente de soporte que clasifica, consulta CRM solo ante prioridad alta y propone una respuesta con revisión humana cuando corresponde.
Decidiría por complejidad, mantenibilidad y capacidades del equipo, considerando también operación, seguridad y costo.

## 2. ¿Cómo evitaría que el costo crezca sin control con el volumen?
Mediría tokens y costo por ejecución, modelo y cliente, incluyendo reintentos, con presupuestos y alertas.
Impondría cuotas, límites de entrada/salida, concurrencia y reintentos, y un corte efectivo al agotar el presupuesto.
Usaría modelos pequeños para tareas simples, contexto mínimo y caché por tenant cuando la vigencia y privacidad lo permitan.
Eliminaría llamadas redundantes y evaluaría calidad/costo antes de cambiar modelos; contrastaría estimaciones con la facturación real.

## 3. ¿Cómo evaluaría la calidad de un agente antes de producción?
Construiría un conjunto versionado de casos reales anonimizados, casos límite y ataques, separado de los ejemplos usados para ajustar prompts.
Mediría clasificación, respuestas fundamentadas, utilidad, fugas de datos, latencia y costo con criterios de aceptación explícitos.
Combinaría verificaciones automáticas con evaluación humana; un modelo evaluador sería apoyo calibrado, no el único juez.
Compararía con una línea base, bloquearía regresiones y haría un despliegue gradual con monitoreo y posibilidad de reversión.

## 4. Un desarrollador junior rompe el pipeline con frecuencia. ¿Cómo lo abordaría?
Revisaría con él fallos concretos, sin culpas, para distinguir problemas de conocimiento, documentación, entorno o pruebas inestables.
Haría pairing en una corrección y dejaríamos comandos locales reproducibles y una guía breve para verificar antes de abrir el PR.
Mantendría PR pequeños, feedback rápido y checks obligatorios antes de integrar; corregiría también las fallas del propio pipeline.
Acordaría seguimiento y mediría la reducción de fallos, dándole autonomía progresiva sin rebajar los controles de calidad.
