"""Historia del juego: «Tenerife Noir · El caso del Faro».

Thriller criminal de ficción. Todo el texto narrativo es fijo y lo controla
Python: el LLM solo responde a las preguntas sobre la isla (con el tono de cada
informante) y nunca decide el avance de la trama. Personajes, nombres y hechos
son inventados.
"""

from __future__ import annotations

from dataclasses import dataclass

PLAYER_NAME = "Ari"
CLUE_REWARD = 500


@dataclass(frozen=True)
class Page:
    """Una pantalla de cinemática."""

    title: str
    text: str


INTRO_PAGES: list[Page] = [
    Page("TENERIFE · 03:12",
         "Muelle de Santa Cruz. Han encontrado a Rubén «El Faro», contrabandista del "
         "puerto, sin vida junto a los contenedores. Nadie vio nada. Nadie oyó nada."),
    Page("EL ALIJO",
         "Esa misma noche desapareció un cargamento que iba a entrar por el puerto: el "
         "alijo «Polvo de Luna». Quien lo tenga sabe quién apagó a El Faro."),
    Page("TU PLACA",
         f"Eres {PLAYER_NAME}, detective de homicidios. La inspectora Salazar te ha citado "
         "en el puerto de Los Cristianos. Ella lleva el caso... y quiere resultados rápidos."),
    Page("LOS SOPLONES",
         "Tres informantes saben algo: Doña Ceniza en el Teide, Toni Grúas en Santa Cruz y "
         "El Lagarto en el monte de Anaga. No hablan gratis: pregúntales por su zona y "
         "suelta la lengua. Cada conversación te dará una pista."),
]

CHAPTERS: dict[str, Page] = {
    "Teide": Page("PISTA 1 · BARRO VOLCÁNICO",
                  "Doña Ceniza mira hacia la cumbre. «Esa noche vi unos faros bajar del Teide "
                  "a toda prisa. El coche llevaba barro volcánico en las ruedas... y el "
                  "escudo de la policía en la puerta.»"),
    "Santa Cruz": Page("PISTA 2 · PAPELES LIMPIOS",
                       "Toni Grúas baja la voz. «Yo solo muevo contenedores, detective. Pero el "
                       "del alijo salió del muelle sin revisar. Lo firmó alguien con placa. "
                       "Firma bonita, con mucha floritura.»"),
    "Anaga": Page("PISTA 3 · LA LIBRETA",
                  "El Lagarto saca una libreta empapada de El Faro. En la última página: "
                  "«Si me pasa algo, la culpa es de quien me prometió protección.» Debajo, "
                  "un nombre tachado que empieza por S."),
}

ENDING_PAGES: list[Page] = [
    Page("ATANDO CABOS",
         "Un coche patrulla con barro del Teide. Un contenedor firmado por alguien con "
         "placa. Una promesa de protección. Solo una persona encaja en las tres."),
    Page("LA INSPECTORA",
         "La inspectora Salazar protegía a El Faro a cambio de su parte. Cuando él quiso "
         "hablar, lo silenció. El alijo estaba en su garaje de Los Cristianos."),
    Page("CASO CERRADO",
         "Salazar ya está en el calabozo y el alijo, requisado. Tenerife duerme tranquila... "
         "por ahora. Puedes seguir patrullando la isla y hablando con tus soplones."),
]

INFORMANT_BY_ZONE = {"Teide": "Doña Ceniza", "Santa Cruz": "Toni Grúas", "Anaga": "El Lagarto"}


def missing_zones(clues: set[str]) -> list[str]:
    """Zonas cuyas pistas faltan, en el orden de la investigación."""
    return [zone for zone in ("Teide", "Santa Cruz", "Anaga") if zone not in clues]


def objective(clues: set[str]) -> str:
    """Objetivo actual mostrado en la interfaz."""
    missing = missing_zones(clues)
    if not missing:
        return "Caso cerrado. Patrulla libre"
    zone = missing[0]
    return f"Interroga a {INFORMANT_BY_ZONE[zone]} ({zone})"


def handler_text(clues: set[str]) -> str:
    """Lo que dice la inspectora Salazar según el avance del caso."""
    missing = missing_zones(clues)
    if len(missing) == 3:
        return ("Llegas tarde, detective. El Faro está frío y el alijo, en paradero desconocido. "
                "Coge la autopista: sube al Teide, pasa por el muelle de Santa Cruz y aprieta "
                "a El Lagarto en Anaga. Pregúntales por la isla hasta que suelten algo.")
    if missing:
        names = ", ".join(INFORMANT_BY_ZONE[z] for z in missing)
        return (f"¿{3 - len(missing)} de 3 pistas? Te queda: {names}. Y no pierdas el tiempo "
                "con preguntas raras... ese caso no es tan complicado como parece.")
    return ("(Salazar te mira desde el asiento trasero del coche patrulla.) «Buen trabajo, "
            "detective. Demasiado bueno.»")
