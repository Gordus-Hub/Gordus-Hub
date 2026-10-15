# PUAC2.md — EXTENSION ARQUITECTONICA CANONICA PROPUESTA

VERSION=2.0.0-CANDIDATE; ID=PUAC-SPEC-2.0.0-CANDIDATE; AUTORIDAD=Louksna.md; ESTADO=EXTENSION_INDEPENDIENTE_PENDIENTE_ADMISION_FORMAL; G23=NO_CONCEDIDA; G24=NO_CONCEDIDA.

Esta entrega preserva íntegramente PUAC 1.0.0 como base documental; las enmiendas v2 son una proyección propuesta y no alteran retroactivamente el texto original. No fusionar ni modificar Louksna.md; no transferir su autoridad. Los ocho controles nuevos conservan identidad local hasta autorización formal.

## PARTE I: PUAC 1.0.0 INTEGRO — BYTES ORIGINALES PRESERVADOS

===============================================================================
PUAC — PROTOCOLO UNIVERSAL DE ASEGURAMIENTO CONTINUO
ESPECIFICACIÓN ARQUITECTÓNICA FORMALIZADA — VERSIÓN 1.0.0
CERTIFICACIÓN POR DISEÑO · EVIDENCIA · COGNICIÓN · GOBERNANZA CONTINUA
===============================================================================

DOCUMENT_ID             = PUAC-SPEC-1.0.0
DOCUMENT_TYPE           = GOVERNED_ARCHITECTURAL_EXTENSION
DESIGN_STATUS           = COMPLETE_FOR_FORMAL_REVIEW
CANONICAL_STATUS        = NOT_INCORPORATED
IMPLEMENTATION_STATUS   = NOT_DEMONSTRATED
VALIDATION_STATUS       = PENDING
INDEPENDENT_VALIDATION  = PENDING
CERTIFICATION_STATUS    = NOT_CERTIFIED
ACTIVATION_STATUS       = PROHIBITED_UNTIL_AUTHORIZED

CANONICAL_AUTHORITY     = Louksna.md
PROTECTED_BASELINE      = LUNACORE_final_formalized_v25.md
GOVERNANCE_DOCTRINE     = EXTEND_DO_NOT_REPLACE
CONSTRUCTION_POLICY     = APPEND_ONLY_WHERE_CANONICAL
FAILURE_POLICY          = FAIL_CLOSED
CERTIFICATION_TRANSFER  = FORBIDDEN
AUTOMATIC_PROMOTION     = FORBIDDEN
SILENT_MUTATION         = FORBIDDEN

DESIGN_OBJECTIVE:

Establecer un protocolo universal en el cual las condiciones
de certificación se definan desde el primer requisito, se
demuestren mediante evidencia suficiente y se vigilen durante
todo el ciclo de vida de cada artefacto.

La universalidad pertenece al procedimiento de aseguramiento.
Las propiedades, pruebas, umbrales y normas sectoriales
dependen del objeto concreto sometido a evaluación.

La especificación no presume que su propia implementación
exista ni que sus garantías ya hayan sido demostradas.

===============================================================================
00. LENGUAJE NORMATIVO Y LÍMITES
===============================================================================

DEBE:
  Obligación ineludible dentro del alcance declarado.

NO DEBE:
  Prohibición ineludible.

PUEDE:
  Facultad permitida únicamente bajo las condiciones expresas.

REQUIERE_AUTORIZACIÓN:
  Acción bloqueada mientras no exista autorización válida.

DESCONOCIDO:
  Estado cuya verdad o falsedad todavía no está demostrada.

CONFLICTO:
  Existencia de evidencias o afirmaciones incompatibles
  sobre una misma propiedad y un mismo contexto.

NO_APLICABLE:
  Clasificación excepcional que requiere fundamento,
  alcance y autorización expresos cuando la política lo permita.

PROHIBICIÓN GENERAL:

Una clasificación NO_APLICABLE, una excepción, un resultado
automatizado o una opinión de un agente NO DEBEN utilizarse
para omitir controles canónicos obligatorios.

LÍMITE EPISTÉMICO:

El PUAC puede verificar sus invariantes formales e impedir
transiciones prohibidas dentro del sistema gobernado.

No presupone conocimiento de todos los hechos externos,
ausencia de vulnerabilidades desconocidas ni infalibilidad
de sensores, evaluadores, modelos o herramientas.

Toda limitación de observación DEBE formar parte del expediente.

===============================================================================
01. PRINCIPIO RECTOR
===============================================================================

P1:
NINGÚN ARTEFACTO SE ACTIVA SIN EVIDENCIA SUFICIENTE
Y AUTORIZACIÓN VÁLIDA.

P2:
NINGUNA AUTORIZACIÓN OPERATIVA PERMANECE EFECTIVA
CUANDO SE CONOCE QUE SUS CONDICIONES CRÍTICAS
HAN DEJADO DE CUMPLIRSE.

P3:
TODA AFIRMACIÓN CRÍTICA DEBE POSEER IDENTIDAD,
ALCANCE, CRITERIOS DE ACEPTACIÓN Y EVIDENCIA TRAZABLE.

P4:
TODO CAMBIO RELEVANTE DEBE PRODUCIR UN ANÁLISIS
EXPLÍCITO DE IMPACTO SOBRE LAS GARANTÍAS EXISTENTES.

P5:
NINGÚN MONITOREO, AUTOMATISMO O MECANISMO NUEVO
PUEDE SUSTITUIR SILENCIOSAMENTE G23 NI G24.

P6:
TODA CONTRADICCIÓN DETECTADA DEBE SER CONSERVADA
COMO EVIDENCIA HASTA SU RESOLUCIÓN GOBERNADA.

P7:
LA CERTIFICACIÓN HISTÓRICA Y LA AUTORIZACIÓN
OPERATIVA ACTUAL SON OBJETOS DIFERENTES.

P8:
LA CERTIFICACIÓN INTERNA NO IMPLICA POR SÍ MISMA
UNA CERTIFICACIÓN EXTERNA O REGULATORIA.

===============================================================================
02. LAS CINCO REGLAS INNEGOCIABLES
===============================================================================

R1 — CERTIFICACIÓN DESDE EL DISEÑO

Ningún requisito crítico se aprueba sin definir:

  - Propiedad que debe demostrarse.
  - Objeto, versión y entorno.
  - Criterio verificable de aceptación.
  - Método de verificación.
  - Método de validación.
  - Evidencia requerida.
  - Riesgos conocidos.
  - Dependencias relevantes.
  - Responsable de la ejecución.
  - Condiciones para la revisión independiente.

R2 — EVIDENCIA VINCULADA

Ninguna afirmación crítica se considera demostrada
sin evidencia identificable, íntegra y suficiente.

Cada evidencia DEBE registrar:

  - Identificador único.
  - Afirmación respaldada o refutada.
  - Fuente y procedencia.
  - Método de obtención.
  - Fecha y secuencia verificables.
  - Herramienta y versión.
  - Objeto y hash evaluados.
  - Resultado y condiciones de ejecución.
  - Limitaciones e incertidumbre.
  - Relaciones de trazabilidad.

R3 — INDEPENDENCIA OBLIGATORIA

G23 y G24 son funciones distintas e irremplazables.

El responsable de construir un artefacto NO DEBE ser
su único evaluador independiente.

La independencia DEBE acreditarse con identidades,
roles, permisos y separación efectiva de funciones.

R4 — VIGENCIA CONDICIONADA

Todo cambio relevante DEBE determinar:

  - Qué afirmaciones resultan afectadas.
  - Qué evidencias conservan su validez.
  - Qué evidencias quedan invalidadas.
  - Qué pruebas deben repetirse.
  - Qué riesgos nuevos aparecen.
  - Si debe intervenir nuevamente G23.
  - Si corresponde una nueva decisión de G24.
  - Si la operación puede continuar.

R5 — CORRECCIÓN CERRADA

Ningún incidente se declara resuelto sin:

  - Registro original e inmutable del incidente.
  - Diagnóstico causal documentado.
  - Decisión de corrección autorizada.
  - Corrección o rollback ejecutado.
  - Verificación del resultado.
  - Pruebas pertinentes de no regresión.
  - Actualización de trazabilidad y evidencia.
  - Reevaluación y recertificación cuando correspondan.

===============================================================================
03. OBJETOS FORMALES Y SEPARACIÓN SEMÁNTICA
===============================================================================

TYPE Artifact:
  artifact_id
  artifact_kind
  version
  content_hash
  manifest_hash
  environment_id
  owner
  criticality
  dependency_graph

TYPE Claim:
  claim_id
  subject_id
  property_id
  scope_id
  context_id
  version
  validity_interval
  acceptance_predicate
  assumptions
  limitations

TYPE Evidence:
  evidence_id
  claim_ids[]
  provenance_id
  source_hash
  method_id
  tool_version
  environment_id
  result
  uncertainty
  observed_at
  causal_parents[]
  integrity_proof

TYPE Evaluation:
  evaluation_id
  claim_id
  evidence_ids[]
  evaluation_method
  evaluator_identity
  criteria_version
  result
  rationale
  limitations

TYPE CertificationDecision:
  decision_id
  artifact_id
  certified_claim_ids[]
  excluded_claim_ids[]
  assurance_profile
  supporting_evidence_hash
  g23_record_id
  authority_id
  decision
  issued_at
  validity_conditions
  supersedes
  signature

TYPE OperationalAuthorization:
  authorization_id
  certificate_id
  permitted_operations[]
  authorized_environment
  risk_acceptance_reference
  monitoring_profile
  authorization_status
  effective_from
  effective_until

TYPE MonitoringObservation:
  observation_id
  artifact_id
  monitored_property
  measured_value
  measurement_method
  event_time
  observed_at
  freshness_status
  evidence_id

TYPE Incident:
  incident_id
  triggering_observations[]
  affected_claims[]
  affected_artifacts[]
  severity
  containment_decision
  remediation_reference
  closure_evidence
  status

REGLA DE TIPOS:

Artifact != Claim
Claim != Evidence
Evidence != Evaluation
Evaluation != CertificationDecision
CertificationDecision != OperationalAuthorization

El resultado de una prueba NO ES una certificación.
La certificación NO ES una autorización operativa perpetua.
El monitoreo NO ES una validación independiente.
La recuperación funcional NO ES una prueba de no regresión.

Ninguna conversión entre estos tipos será implícita.

===============================================================================
04. IDENTIDAD, UNICIDAD Y CONTRADICCIÓN
===============================================================================

IDENTIDAD CANÓNICA:

La identidad de un objeto se determina mediante el
identificador y la versión autorizados por su registro.

Un nombre parecido, traducción, abreviatura o relación
etimológica NO constituye identidad equivalente.

CLAIM_KEY:

  subject_id
  property_id
  scope_id
  context_id
  version
  validity_interval
  unit_of_measure

Dos afirmaciones sólo pueden compararse como una
contradicción directa después de comprobar que sus
CLAIM_KEY y sus definiciones semánticas son compatibles.

EJEMPLOS:

  Afirmación sobre V1 != afirmación sobre V2.

  Medición en un entorno != medición en otro entorno.

  Resultado observado != garantía universal.

  Recuento de tokens != recuento de definiciones.

  Equivalencia terminológica != equivalencia de autoridad.

INVARIANTE DE PROYECCIÓN:

Para una misma CLAIM_KEY no puede existir más de un
valor normativo activo incompatible.

Las afirmaciones históricas contradictorias permanecen
en el registro de evidencia, pero no pueden proyectarse
simultáneamente como una única verdad normativa.

MODELO DE EVIDENCIA DE CUATRO ESTADOS:

  SUPPORTED = existe respaldo y no existe refutación válida.
  REFUTED   = existe refutación y no existe respaldo válido.
  UNKNOWN   = respaldo y refutación insuficientes.
  CONFLICT  = existen respaldo y refutación incompatibles.

Este modelo describe el estado de la evidencia;
no reemplaza los estados canónicos de Louksna.

REGLA DE DECISIÓN BINARIA:

  PERMIT = TRUE únicamente si todas las precondiciones
  obligatorias están demostradas.

  PERMIT = FALSE ante REFUTED, UNKNOWN, CONFLICT
  o ausencia de una precondición obligatoria.

La lógica binaria se aplica a la decisión de autorización.
No se utiliza para ocultar incertidumbre empírica.

===============================================================================
05. PRESERVACIÓN CANÓNICA Y REGISTRO DE CONTROLES
===============================================================================

PRESERVE:

  B1-B134
  AX0001-AX12414
  FOUR_CANONICAL_AGENTS
  FOURTEEN_CANONICAL_COMMANDS
  E01-E15
  CFE001-CFE074
  G01-G24
  DOC0001-DOC0022

Las identidades y relaciones autorizadas se obtienen
del registro canónico vigente, no de reconstrucciones
por semejanza textual.

REGISTRO DE CONTROLES PREEXISTENTES:

G01 = SOURCE_INTEGRITY
G02 = BASELINE_INTEGRITY
G03 = SEMANTIC_EQUIVALENCE
G04 = IDENTITY_PRESERVATION
G05 = SCOPE_PRESERVATION
G06 = FUNCTION_PRESERVATION
G07 = RELATION_PRESERVATION
G08 = RESPONSIBILITY_PRESERVATION
G09 = AGENT_COMPATIBILITY
G10 = COMMAND_COMPATIBILITY
G11 = ENGINE_COMPATIBILITY
G12 = CFE_COMPATIBILITY
G13 = PYTHON_LIBRARY_COMPATIBILITY
G14 = REFORMED_BIBLICAL_DICTIONARY_VALIDATION
G15 = HERMENEUTICAL_NON_REGRESSION
G16 = CAPABILITY_NON_DUPLICATION
G17 = TRAINING_INTEGRITY
G18 = STRESS_TEST_VALIDATION
G19 = PROVENANCE
G20 = AUDITABILITY
G21 = ROLLBACK
G22 = GLOBAL_NON_REGRESSION
G23 = INDEPENDENT_VALIDATION
G24 = CERTIFICATION

G01-G24 conservan su identidad, semántica, autoridad
y condiciones de aplicación canónicas.

PUAC NO los redefine.

Los nuevos controles se registran inicialmente con
identificadores locales, evitando ocupar silenciosamente
un espacio canónico.

IDENTIFICADOR LOCAL       IDENTIFICADOR PROPUESTO

PUAC.C25                 G25
PUAC.C26                 G26
PUAC.C27                 G27
PUAC.C28                 G28
PUAC.C29                 G29
PUAC.C30                 G30
PUAC.C31                 G31
PUAC.C32                 G32

La promoción de cada identificador requiere comprobar
disponibilidad, compatibilidad y aprobación expresa.

===============================================================================
06. OCHO CONTROLES COMPLEMENTARIOS
===============================================================================

PUAC.C25 — ALCANCE Y AFIRMACIONES

INPUT:
  Artifact
  Claims[]
  IntendedUse
  Environment
  AssuranceProfile

OUTPUT:
  ApprovedScope
  ClaimRegistry
  AcceptanceCriteria
  Exclusions
  ScopeEvidence

PRECONDITIONS:
  Identidad inequívoca.
  Versión identificada.
  Propiedades no ambiguas.
  Criterios verificables.
  Supuestos declarados.

DENY IF:
  Alcance abierto o contradictorio.
  Afirmaciones sin criterio de aceptación.
  Propiedades críticas omitidas sin autorización.

-----------------------------------------------------------------------

PUAC.C26 — EVIDENCIA Y ARGUMENTACIÓN

INPUT:
  ApprovedScope
  Claims[]
  Evidence[]
  Assumptions[]

OUTPUT:
  AssuranceCase
  EvidenceCoverage
  UnresolvedClaims
  ArgumentationRecord

PRECONDITIONS:
  Cada afirmación posee una cadena argumentativa.
  Cada evidencia conserva su procedencia.
  Las inferencias declaran sus premisas.
  Las limitaciones son visibles.

DENY IF:
  Evidencia ausente.
  Argumentación circular.
  Fuente no identificada.
  Afirmación más fuerte que sus pruebas.

-----------------------------------------------------------------------

PUAC.C27 — INDEPENDENCIA ESTRUCTURAL

INPUT:
  ActorRegistry
  RoleAssignments
  EvaluationPlan
  ConflictOfInterestRecords

OUTPUT:
  IndependenceAssessment
  AllowedEvaluators
  SeparationEvidence

PRECONDITIONS:
  Ejecutores y evaluadores identificados.
  Permisos verificables.
  Conflictos declarados.
  Separación efectiva según criticidad.

DENY IF:
  Autoevaluación presentada como independiente.
  Identidades no verificadas.
  Dependencia incompatible con el perfil aplicable.

Este control prepara y verifica las condiciones
estructurales de independencia.

NO sustituye el juicio técnico de G23.

-----------------------------------------------------------------------

PUAC.C28 — SEGURIDAD Y RIESGOS

INPUT:
  Artifact
  ThreatModel
  DependencyGraph
  IntendedUse
  RiskCriteria

OUTPUT:
  RiskRegister
  ThreatAssessment
  TreatmentPlan
  ResidualRiskRecord

PRECONDITIONS:
  Amenazas identificadas.
  Riesgos clasificados.
  Tratamientos trazables.
  Riesgos residuales expresos.

DENY IF:
  Riesgo crítico prohibido.
  Dependencia esencial desconocida.
  Riesgo residual no autorizado.
  Vulnerabilidad crítica incompatible con la política.

La aceptación de riesgos no autoriza violar
un invariante canónico.

-----------------------------------------------------------------------

PUAC.C29 — INTEGRIDAD Y REPRODUCIBILIDAD

INPUT:
  ArtifactBytes
  Manifest
  DependencyLock
  BuildRecipe
  ExecutionEnvironment

OUTPUT:
  IntegrityReport
  ReproductionReport
  ProvenanceAttestation
  SupplyChainEvidence

PRECONDITIONS:
  Hashes íntegros.
  Versiones fijadas.
  Procedencia identificada.
  Entorno declarado.
  Resultados reproducibles cuando se afirme reproducibilidad.

DENY IF:
  Hash incorrecto.
  Dependencia no identificada.
  Artefacto diferente del evaluado.
  Reproducibilidad afirmada pero no demostrada.

Hash correcto demuestra coincidencia de contenido
respecto del valor esperado.

NO demuestra por sí solo autenticidad,
ausencia de malware ni corrección funcional.

-----------------------------------------------------------------------

PUAC.C30 — INTEGRACIÓN Y NO REGRESIÓN

INPUT:
  PreviousBaseline
  CandidateBuild
  ChangeSet
  DependencyGraph
  PreviousEvidence

OUTPUT:
  ImpactGraph
  RegressionResults
  PreservedClaims
  InvalidatedClaims
  RevalidationPlan

PRECONDITIONS:
  Diferencias identificadas.
  Dependencias directas e indirectas examinadas.
  Pruebas afectadas determinadas.
  Invariantes preservados o bloqueados.

DENY IF:
  Cambio indirecto inexplicado.
  Pérdida semántica no autorizada.
  Regresión crítica.
  Evidencia invalidada reutilizada como vigente.

La certificación de A1 y A2 no certifica
automáticamente la integración A3.

-----------------------------------------------------------------------

PUAC.C31 — REVERSIBILIDAD DEMOSTRADA

INPUT:
  OperationPlan
  Checkpoint
  RestorationProcedure
  ExpectedState

OUTPUT:
  RollbackTest
  RestorationEvidence
  RecoveryLimitations

PRECONDITIONS:
  Checkpoint verificado.
  Restauración ensayada.
  Integridad posterior comprobada.
  Pérdidas y limitaciones identificadas.

DENY IF:
  Checkpoint inválido.
  Restauración no demostrada.
  Estado recuperado no verificado.
  Dependencia oculta impide recuperar el sistema.

Una acción compensatoria no se clasificará
automáticamente como rollback.

Cuando una operación irreversible requiera rollback
por mandato canónico, su ejecución será bloqueada.

-----------------------------------------------------------------------

PUAC.C32 — VIGENCIA Y REEVALUACIÓN

INPUT:
  CertificationDecision
  OperationalAuthorization
  MonitoringProfile
  Observations[]
  ChangeEvents[]

OUTPUT:
  AssuranceStatus
  ImpactAssessment
  SuspensionRecommendation
  RevalidationRequest
  RecertificationRequest

PRECONDITIONS BEFORE INITIAL CERTIFICATION:
  Estrategia de vigilancia definida.
  Propiedades observables identificadas.
  Frecuencias y eventos establecidos.
  Procedimiento de incidentes ensayado.
  Responsables asignados.

PRECONDITIONS DURING OPERATION:
  Observaciones dentro de la vigencia requerida.
  Integridad del monitoreo comprobada.
  Incidentes gestionados según política.
  Autorización todavía válida.

DENY IF:
  Monitoreo obligatorio ausente.
  Observaciones vencidas.
  Desviación crítica sin contención.
  Certificado suspendido o revocado.
  Autorización operativa inválida.

===============================================================================
07. CAPA METACOGNITIVA Y COGNITIVA
===============================================================================

MODULE_NAMESPACE = PUAC.MC
MODULE_COUNT     = 8
AUTHORITY        = ADVISORY_WITH_DETERMINISTIC_GUARDS
CERTIFY_PERMISSION = NONE
CANONICAL_MUTATION_PERMISSION = NONE

La capa metacognitiva inspecciona la calidad
de las afirmaciones, el razonamiento, las relaciones
semánticas y las decisiones propuestas.

Sus resultados son evidencia auxiliar y entradas
para verificadores deterministas.

Un modelo de IA NO puede convertir su propio juicio
en certificación independiente.

-----------------------------------------------------------------------

PUAC.MC.01 — ANÁLISIS ETIMOLÓGICO

OBJETIVO:
  Identificar origen, evolución y relaciones de términos
  relevantes para la precisión conceptual.

CONTRATO:
  INPUT  = {TERM, LANGUAGE, SOURCE, HISTORICAL_CONTEXT}
  OUTPUT = {ETYMOLOGICAL_ANALYSIS, SOURCES, UNCERTAINTY}

CONTROLES:
  No deducir significado actual únicamente de la etimología.
  No convertir parentesco léxico en identidad de conceptos.
  No derivar autoridad canónica del origen de una palabra.

-----------------------------------------------------------------------

PUAC.MC.02 — ANÁLISIS FILOLÓGICO Y SEMÁNTICO

OBJETIVO:
  Preservar el sentido de los textos, las definiciones
  y los identificadores dentro de sus contextos.

CONTRATO:
  INPUT  = {SOURCE_TEXT, SOURCE_VERSION, LANGUAGE, CONTEXT}
  OUTPUT = {SEMANTIC_MAP, AMBIGUITIES, VARIANTS, TRACE}

CONTROLES:
  Diferenciar texto original de interpretación.
  Registrar variantes y traducciones.
  Preservar el texto fuente byte-exact cuando esté congelado.
  Producir vistas normalizadas sólo mediante reglas reversibles.
  No efectuar sustituciones semánticas silenciosas.

-----------------------------------------------------------------------

PUAC.MC.03 — ANÁLISIS CRONOLÓGICO Y CAUSAL

OBJETIVO:
  Reconstruir el orden de eventos, versiones,
  autorizaciones, cambios y efectos.

CONTRATO:
  INPUT  = {EVENT_LOG, TIMESTAMPS, CAUSAL_PARENTS}
  OUTPUT = {CHRONOLOGY, CAUSAL_GRAPH, TIME_CONFLICTS}

CONTROLES:
  Distinguir tiempo del evento y tiempo de observación.
  Distinguir precedencia temporal y causalidad.
  Comprobar secuencias y dependencias.
  Detectar referencias al futuro y ciclos causales.
  No inventar un orden cuando el registro es insuficiente.

-----------------------------------------------------------------------

PUAC.MC.04 — LÓGICA FORMAL Y CONSISTENCIA

OBJETIVO:
  Transformar invariantes y contratos aplicables
  en propiedades formalmente comprobables.

CONTRATO:
  INPUT  = {TYPED_CLAIMS, INVARIANTS, STATE_MODEL}
  OUTPUT = {PROOF_OBLIGATIONS, RESULTS, COUNTEREXAMPLES}

CONTROLES:
  Verificación de tipos.
  Comprobación de unicidad.
  Ausencia de transiciones prohibidas.
  Coherencia entre precondiciones y resultados.
  Comprobación de contradicciones dentro de un alcance definido.

Las herramientas de demostración y los modelos
utilizados deben identificarse y versionarse.

Una propiedad no demostrada permanece NO_DEMOSTRADA.

-----------------------------------------------------------------------

PUAC.MC.05 — LÓGICA BINARIA Y EJECUCIÓN

OBJETIVO:
  Convertir las condiciones normativas comprobadas
  en decisiones inequívocas de ejecución.

CONTRATO:
  INPUT  = {REQUEST, AUTHORIZATION, PRECONDITIONS, STATE}
  OUTPUT = {ALLOW_OR_DENY, REASON_CODE, AUDIT_EVENT}

CONTROLES:
  Permiso denegado por defecto.
  Identidad y autorización obligatorias.
  Evaluación determinista de condiciones explícitas.
  Ninguna condición UNKNOWN o CONFLICT se interpreta como PASS.

-----------------------------------------------------------------------

PUAC.MC.06 — EMPIRISMO Y CONTROL EPISTÉMICO

OBJETIVO:
  Distinguir lo observado de lo inferido y evaluar
  empíricamente las afirmaciones que lo requieran.

CONTRATO:
  INPUT  = {HYPOTHESIS, DATA, METHOD, RESULTS, LIMITATIONS}
  OUTPUT = {EMPIRICAL_FINDINGS, UNCERTAINTY, VALIDITY}

CONTROLES:
  Separar datos, hipótesis e interpretación.
  Declarar sesgos y limitaciones.
  Controlar contaminación de conjuntos de prueba.
  Registrar reproducibilidad y variabilidad.
  No universalizar resultados limitados.

Para sistemas probabilísticos, los umbrales
estadísticos deben definirse antes de evaluar.

-----------------------------------------------------------------------

PUAC.MC.07 — RAZONAMIENTO Y ANÁLISIS DE SEGUNDO ORDEN

OBJETIVO:
  Evaluar consecuencias directas e indirectas
  de propuestas, cambios y correcciones.

CONTRATO:
  INPUT  = {PROPOSAL, CAUSAL_GRAPH, CONSTRAINTS, EVIDENCE}
  OUTPUT = {IMPACT_ANALYSIS, ALTERNATIVES, JUSTIFICATION}

CONTROLES:
  Identificar premisas.
  Distinguir deducción, inducción y abducción.
  Examinar dependencias indirectas.
  Considerar contraejemplos.
  Registrar hipótesis no demostradas.

Una justificación generada por IA no constituye
por sí misma prueba formal ni evaluación independiente.

-----------------------------------------------------------------------

PUAC.MC.08 — METACOGNICIÓN Y AUTOCONTROL

OBJETIVO:
  Inspeccionar la calidad del proceso de razonamiento
  y detectar errores en sus propias conclusiones.

CONTRATO:
  INPUT  = {CLAIMS, EVIDENCE, METHODS, DECISION_PROPOSALS}
  OUTPUT = {SELF_AUDIT, UNCERTAINTY_REGISTER, ESCALATIONS}

CONTROLES:
  Identificar supuestos ocultos.
  Detectar extrapolaciones.
  Comprobar coherencia interdisciplinaria.
  Identificar evidencia insuficiente.
  Separar hechos, interpretaciones y decisiones.
  Recomendar abstención o revisión cuando corresponda.

La metacognición mejora el control epistemológico,
pero NO sustituye verificadores, evaluadores
independientes ni autoridades de certificación.

===============================================================================
08. CONTRATOS DE INTERFAZ
===============================================================================

INTERFACE REGISTER_ARTIFACT

INPUT:
  ManifestCandidate
  ActorIdentity

PRE:
  Actor autorizado.
  Identificador disponible.
  Esquema válido.
  Referencias canónicas comprobadas.

POST:
  Objeto registrado en estado DECLARED.
  Evento de auditoría emitido.

FAIL:
  DENY_AND_RECORD.

-----------------------------------------------------------------------

INTERFACE SUBMIT_CLAIM

INPUT:
  ArtifactReference
  TypedClaim
  AcceptanceCriteria

PRE:
  Artefacto registrado.
  Alcance definido.
  Tipos y unidades válidos.
  Ausencia de colisión de identidad.

POST:
  Afirmación registrada.
  Obligaciones de prueba creadas.

FAIL:
  QUARANTINE_CONFLICTING_CLAIM.

-----------------------------------------------------------------------

INTERFACE ATTACH_EVIDENCE

INPUT:
  ClaimReference
  EvidencePackage
  ProvenanceRecord

PRE:
  Fuente identificada.
  Hash válido.
  Método declarado.
  Objeto y alcance coincidentes.

POST:
  Evidencia añadida al registro inmutable.
  Relaciones de trazabilidad actualizadas.

FAIL:
  REJECT_EVIDENCE_AND_RECORD.

-----------------------------------------------------------------------

INTERFACE VERIFY

INPUT:
  ClaimReference
  VerificationPlan
  EvidenceSet

PRE:
  Criterios de aceptación definidos.
  Herramientas autorizadas.
  Entorno identificado.

POST:
  Informe de verificación reproducible.
  PASS, FAIL, UNKNOWN o CONFLICT.

FAIL:
  BLOCK_ADVANCEMENT.

-----------------------------------------------------------------------

INTERFACE REQUEST_G23

INPUT:
  AssuranceCase
  VerificationReport
  IndependenceEvidence

PRE:
  Expediente completo.
  Evaluador independiente autorizado.
  Conflictos de interés resueltos.

POST:
  Decisión independiente registrada.
  Deficiencias y limitaciones explícitas.

FAIL:
  CERTIFICATION_READY = FALSE.

-----------------------------------------------------------------------

INTERFACE REQUEST_G24

INPUT:
  AssuranceCase
  ApplicableGateResults
  G23Decision
  RiskRecord
  CertificationScope

PRE:
  Todos los controles obligatorios satisfechos.
  G23 favorable.
  Ausencia de conflictos críticos abiertos.
  Autoridad competente autenticada.

POST:
  Decisión firmada de aprobación o denegación.
  Alcance, vigencia y condiciones identificados.

FAIL:
  NO_CERTIFICATE_ISSUED.

-----------------------------------------------------------------------

INTERFACE AUTHORIZE_OPERATION

INPUT:
  CertificateReference
  ArtifactReference
  Environment
  MonitoringProfile
  OperatorIdentity

PRE:
  Certificado aplicable y vigente.
  Identidad binaria coincidente.
  Riesgos autorizados.
  Monitoreo obligatorio preparado.
  Operador autorizado.

POST:
  Autorización operativa explícita.
  Permisos limitados por alcance.

FAIL:
  DENY_OPERATION.

-----------------------------------------------------------------------

INTERFACE OBSERVE_AND_REASSESS

INPUT:
  MonitoringObservations
  ChangeEvents
  ActiveAuthorizations

PRE:
  Identidad del sistema verificada.
  Integridad del registro.
  Política de vigilancia vigente.

POST:
  Evaluación de impacto.
  Conservación o invalidación de evidencia.
  Incidentes y solicitudes de reevaluación.

FAIL:
  MARK_OBSERVABILITY_GAP;
  APPLY_FAIL_CLOSED_POLICY.

-----------------------------------------------------------------------

INTERFACE RECOVER

INPUT:
  Incident
  AuthorizedRecoveryPlan
  VerifiedCheckpoint

PRE:
  Autoridad de recuperación confirmada.
  Checkpoint íntegro.
  Alcance del rollback definido.

POST:
  Estado restaurado y verificado.
  Evidencia de recuperación registrada.
  Solicitudes de revalidación emitidas.

FAIL:
  QUARANTINE;
  ESCALATE_WITHOUT_FALSE_RECOVERY_CLAIM.

===============================================================================
09. CONTRATO DEL MANIFIESTO
===============================================================================

MANIFEST_SCHEMA = puac.manifest/1.0.0

REQUIRED_FIELDS:

  manifest_id
  schema_version
  project_id
  artifact_id
  artifact_type
  artifact_version
  artifact_hash
  canonical_authority_ref
  baseline_hash
  assurance_profile_ref
  owner_id
  executor_id
  verifier_id
  independent_validator_id
  certification_authority_id
  certification_scope
  critical_claims[]
  acceptance_criteria[]
  dependencies[]
  evidence_registry_ref
  traceability_graph_ref
  risk_register_ref
  test_plan_ref
  rollback_plan_ref
  monitoring_profile_ref
  change_policy_ref
  authorization_policy_ref

DATA_CONSTRAINTS:

  Identificadores no vacíos.
  Referencias resolubles.
  Versiones explícitas.
  Hashes SHA-256 representados como 64 caracteres hexadecimales.
  Tamaños expresados en bytes enteros.
  Fechas ISO 8601 con zona horaria explícita.
  Identificadores sin colisiones.
  Claves JSON duplicadas prohibidas.
  Campos desconocidos tratados según la versión del esquema.

SERIALIZATION:

  JSON canónico compatible con RFC 8785 cuando
  se seleccione ese formato para hashes o firmas.

  El material protegido original se conserva por bytes.

  Una vista normalizada para lectura no altera
  el hash del documento fuente.

MANIFEST_INTEGRITY:

  El hash del manifiesto se calcula excluyendo
  únicamente el campo que contiene su propio hash,
  mediante una regla de serialización previamente definida.

  Las firmas se almacenan en una envoltura separada
  para evitar dependencias criptográficas circulares.

  La gestión y protección de claves corresponde
  a una política de seguridad independiente.

MISSING_REQUIRED_FIELD:

  MANIFEST_STATUS = INVALID
  ACTIVATION = DENIED

===============================================================================
10. CONTRATO DE TRAZABILIDAD BIDIRECCIONAL
===============================================================================

REQUIRED_GRAPH:

  REQUIREMENT
      <-> CLAIM
      <-> DESIGN_COMPONENT
      <-> IMPLEMENTATION
      <-> TEST
      <-> RESULT
      <-> EVIDENCE
      <-> G23_REVIEW
      <-> G24_DECISION
      <-> OPERATIONAL_MONITOR
      <-> CHANGE_EVENT
      <-> INCIDENT
      <-> REMEDIATION

Cada relación DEBE declarar:

  edge_id
  source_id
  target_id
  relationship_type
  scope
  validity_interval
  provenance
  evidence_reference

TRACEABILITY_INVARIANTS:

  Todo requisito crítico tiene afirmación verificable.

  Toda afirmación crítica tiene evidencia suficiente
  antes de alcanzar el estado VALIDATED.

  Toda decisión G24 referencia su evaluación G23.

  Toda autorización referencia una decisión G24 aplicable.

  Toda observación relevante referencia el control
  o propiedad que vigila.

  Todo cambio identifica su impacto directo e indirecto.

  Toda invalidación de evidencia se propaga
  a las afirmaciones y autorizaciones dependientes.

Una relación ausente no puede inferirse por parecido
de nombres, proximidad textual o consenso de agentes.

===============================================================================
11. CONTRATO DE AUDITORÍA Y PROCEDENCIA
===============================================================================

AUDIT_MODEL = APPEND_ONLY_EVENT_LOG

EVENT_RECORD:

  event_id
  sequence_number
  event_type
  actor_id
  role_id
  action
  object_id
  object_version
  object_hash
  scope
  tool_id
  tool_version
  event_time_utc
  observed_at_utc
  causal_parents[]
  input_evidence_hashes[]
  output_evidence_hashes[]
  previous_event_hash
  current_event_hash
  authorization_reference
  result
  failure_reason
  recovery_reference
  signature_if_required

El registro DEBE conservar eventos exitosos,
fallidos, rechazados, suspendidos y revertidos.

Una rectificación se registra como evento adicional.

Los eventos anteriores NO DEBEN sobrescribirse.

INTEGRITY:

  La cadena de hashes debe verificarse desde
  un punto de confianza conocido.

  Los registros críticos deben protegerse
  contra modificación y eliminación no autorizadas.

  Los mecanismos de firma y anclaje externo
  se definen conforme al perfil de riesgo.

La integridad criptográfica del registro no demuestra
por sí sola que todos los eventos del mundo real
hayan sido observados.

DATA_PROTECTION:

  La evidencia sensible se protege mediante
  controles de acceso y retención.

  Una copia redactada conserva referencia
  verificable al original protegido.

  Ninguna necesidad de auditabilidad autoriza
  la exposición indiscriminada de secretos.

===============================================================================
12. CONTROL CRONOLÓGICO Y TEMPORAL
===============================================================================

TIME_FIELDS:

  event_time:
    Momento declarado de ocurrencia.

  observed_at:
    Momento de recepción o detección.

  recorded_at:
    Momento de incorporación al registro.

  effective_from:
    Inicio de vigencia jurídica u operativa interna.

  effective_until:
    Fin explícito de vigencia, cuando exista.

  sequence_number:
    Orden lógico dentro del registro correspondiente.

  causal_parents:
    Eventos de los que depende causalmente un evento.

RULES:

  No inferir causalidad de la mera precedencia temporal.

  Los eventos con relojes no confiables deben
  conservar su incertidumbre cronológica.

  Los grafos de precedencia causal no admiten ciclos.

  Una certificación no puede fundamentarse
  en evidencia posterior no incorporada a su expediente.

  Las decisiones posteriores no reescriben
  la verdad histórica de decisiones anteriores.

  Toda corrección retroactiva debe registrar
  su fecha de descubrimiento y su alcance.

===============================================================================
13. MODELO FORMAL DE ESTADOS
===============================================================================

CANONICAL_EPISTEMIC_SEQUENCE:

  DECLARED
      ->
  EVIDENCED
      ->
  VALIDATED
      ->
  INDEPENDENTLY_VALIDATED
      ->
  CERTIFIED
      ->
  ACTIVE

La secuencia canónica se conserva.

La verificación y los controles complementarios
aportan condiciones y evidencia a esas transiciones.

No se introduce un atajo ni se altera el orden.

OPERATIONAL_PROJECTION:

  INACTIVE
  AUTHORIZED
  ACTIVE
  UNDER_REEVALUATION
  SUSPENDED
  QUARANTINED
  RECOVERING

Estos estados describen la proyección operativa vigente;
no sustituyen ni reescriben el historial epistemológico.

CERTIFICATE_PROJECTION:

  NOT_ISSUED
  EFFECTIVE
  SUSPENDED
  SUPERSEDED
  REVOKED
  EXPIRED

Una certificación histórica permanece registrada
aunque posteriormente sea suspendida o revocada.

AUTHORIZED_OPERATION:

  Requiere simultáneamente:

    Certificación aplicable.
    Autorización operativa vigente.
    Artefacto y entorno coincidentes.
    Controles críticos satisfechos.
    Monitoreo dentro de los límites establecidos.

===============================================================================
14. OBLIGACIONES FORMALES DE PRUEBA
===============================================================================

INV-01 — IDENTIDAD

Para toda identidad canónica y versión activa,
existe una única asignación autorizada.

INV-02 — NO SUSTITUCIÓN

Ningún control complementario puede asumir
la autoridad ni el significado de G23 o G24.

INV-03 — CERTIFICACIÓN

CERTIFIED sólo puede alcanzarse mediante
una decisión G24 válida y vinculada al objeto exacto.

INV-04 — INDEPENDENCIA

G24 no puede aprobar una solicitud cuando
la evidencia obligatoria de G23 es insuficiente.

INV-05 — ACTIVACIÓN

ACTIVE implica certificación aplicable,
autorización vigente y condiciones operativas satisfechas.

INV-06 — INTEGRIDAD

Los hashes de artefacto, manifiesto y evidencia
deben corresponder a los objetos realmente evaluados.

INV-07 — TRAZABILIDAD

Toda afirmación crítica certificada posee
un camino verificable hasta su evidencia y decisión.

INV-08 — NO REGRESIÓN

Ningún cambio puede reutilizar como vigente
una evidencia que el análisis de impacto haya invalidado.

INV-09 — AISLAMIENTO

Ningún dominio modifica silenciosamente
otro dominio ni sus dependencias compartidas.

INV-10 — AUDITORÍA

Toda decisión y toda mutación gobernada
producen un evento de auditoría.

INV-11 — FALLO CERRADO

Ninguna condición obligatoria UNKNOWN,
CONFLICT o FAIL puede interpretarse como PASS.

INV-12 — ROLLBACK

Toda restauración declarada exitosa debe estar
respaldada por verificación del estado restaurado.

INV-13 — NO PROPAGACIÓN

La certificación de un componente no implica
certificación automática de su integración.

INV-14 — VIGENCIA

Una autorización afectada por un incumplimiento
crítico conocido no permanece operativamente habilitada.

INV-15 — AUTORIDAD

Ningún agente, motor o recurso externo adquiere
autoridad canónica por éxito computacional.

INV-16 — EVIDENCIA HISTÓRICA

Ninguna corrección destruye los registros que
permiten reconstruir la desviación original.

PROOF_POLICY:

  Los invariantes deterministas deben traducirse
  a verificadores, restricciones o modelos formales
  cuando sea técnicamente viable.

  Los resultados de demostración deben registrar
  herramienta, versión, modelo, hipótesis y alcance.

  Una demostración pendiente no puede declararse PASS.

  Las propiedades empíricas requieren pruebas
  adicionales y no se presentan como teoremas.

===============================================================================
15. DETECCIÓN, CLASIFICACIÓN Y RESOLUCIÓN DE CONTRADICCIONES
===============================================================================

CONFLICT_PIPELINE:

  DETECT
      ->
  PRESERVE_RAW_EVIDENCE
      ->
  IDENTIFY_CLAIM_KEYS
      ->
  CHECK_CONTEXT_AND_VERSION
      ->
  CLASSIFY
      ->
  ASSESS_IMPACT
      ->
  CONTAIN
      ->
  INVESTIGATE
      ->
  PROPOSE_RESOLUTION
      ->
  VERIFY_RESOLUTION
      ->
  G23_IF_REQUIRED
      ->
  G24_IF_REQUIRED
      ->
  UPDATE_PROJECTION
      ->
  CONTINUE_MONITORING

CONFLICT_CLASSES:

  IDENTITY_COLLISION
  SEMANTIC_CONFLICT
  TYPE_MISMATCH
  SCOPE_MISMATCH
  VERSION_MISMATCH
  TEMPORAL_CONFLICT
  EVIDENCE_CONFLICT
  AUTHORITY_CONFLICT
  LOGICAL_CONTRADICTION
  EMPIRICAL_DISAGREEMENT
  IMPLEMENTATION_DIVERGENCE
  CERTIFICATION_CONFLICT

RESOLUTION_RULES:

  1. Conservar ambas afirmaciones originales.

  2. Verificar que hablan realmente del mismo objeto,
     propiedad, período, alcance y unidad.

  3. Identificar las fuentes y su autoridad aplicable.

  4. Determinar si existe una contradicción real,
     una diferencia contextual o una ambigüedad.

  5. Bloquear únicamente las operaciones afectadas,
     salvo que el riesgo exija contención más amplia.

  6. Emitir una propuesta de resolución trazable.

  7. No modificar contenido canónico congelado.

  8. Exigir autorización expresa para cualquier
     nueva proyección o corrección normativa.

  9. Repetir las pruebas y evaluaciones pertinentes.

 10. Registrar tanto la resolución como las
     discrepancias que permanezcan abiertas.

FORBIDDEN:

  LAST_WRITE_WINS_WITHOUT_AUTHORITY
  SILENT_REPLACEMENT
  SILENT_RECLASSIFICATION
  FABRICATED_CONSENSUS
  UNDOCUMENTED_NORMALIZATION
  FALSE_CERTIFICATION

Si el conflicto no puede resolverse con evidencia
suficiente, su estado permanece CONFLICT o UNKNOWN.

La ausencia de resolución no autoriza inventar una.

===============================================================================
16. GOBERNANZA, ROLES Y SEGREGACIÓN
===============================================================================

ROLE EXECUTOR:
  Construye o modifica el objeto autorizado.
  Produce evidencia de ejecución.
  No se autocertifica.

ROLE VERIFIER:
  Ejecuta las pruebas especificadas.
  Informa resultados y limitaciones.

ROLE INDEPENDENT_VALIDATOR:
  Ejecuta G23 bajo condiciones demostrables
  de independencia.

ROLE CERTIFICATION_AUTHORITY:
  Ejecuta G24 y emite la decisión formal
  conforme al alcance de su autoridad.

ROLE MONITOR:
  Observa propiedades y condiciones operativas.
  No concede certificaciones.

ROLE INCIDENT_GOVERNOR:
  Autoriza la contención, recuperación y
  escalamiento dentro de sus competencias.

ROLE CANONICAL_AUTHORITY:
  Controla las modificaciones autorizadas
  del estado arquitectónico canónico.

ROLE HUMAN_OVERSIGHT:
  Interviene cuando la política exige
  supervisión o aceptación de riesgos humana.

PERMISSIONS:

  Todo permiso tiene sujeto, acción, objeto,
  alcance, vigencia y evidencia de autorización.

  Los privilegios mínimos son obligatorios.

  La separación entre ejecución, G23 y G24
  debe demostrarse según el perfil de aseguramiento.

  Las herramientas auxiliares no adquieren
  por ello el papel de ejecutor principal.

  Ninguna asignación temporal puede alterar
  silenciosamente las funciones canónicas de los agentes.

===============================================================================
17. PERFILES DE ASEGURAMIENTO
===============================================================================

El PUAC permite distintos perfiles internos.

Un perfil no es una acreditación externa
ni equivale automáticamente a EAL, DAL o SIL.

PROFILE STANDARD:

  Contratos completos.
  Evidencia verificable.
  Controles canónicos aplicables.
  G23 y G24 obligatorios.
  Monitoreo conforme al riesgo.
  No regresión y recuperación demostradas.

PROFILE ELEVATED:

  Incluye STANDARD.
  Mayor independencia estructural.
  Pruebas negativas y adversariales ampliadas.
  Análisis transitorio de dependencias.
  Controles reforzados de procedencia.
  Ensayos de incidentes y recuperación.

PROFILE CRITICAL:

  Incluye ELEVATED.
  Evidencia completa de todos los requisitos críticos.
  Demostración formal selectiva de invariantes verificables.
  Evaluación independiente reforzada.
  Pruebas adversariales específicas.
  Ensayos de fallo y restauración.
  Control estricto de cambios.
  Vigilancia con límites de frescura explícitos.
  Suspensión automática de operaciones afectadas
  cuando fallen condiciones críticas verificables.

PROFILE_SELECTION:

  Se determina antes de las pruebas mediante
  análisis de criticidad y riesgo.

  No puede reducirse retrospectivamente
  para justificar una entrega fallida.

  Los umbrales medibles pertenecen al manifiesto
  del perfil y no se inventan durante la evaluación.

===============================================================================
18. ASEGURAMIENTO CONTINUO
===============================================================================

MONITORING_POLICY:

  PROPERTY_SET
  SENSOR_SET
  COLLECTION_METHOD
  FREQUENCY
  EVENT_TRIGGERS
  MAX_EVIDENCE_AGE
  DETECTION_LIMITATIONS
  ALERT_THRESHOLDS
  RESPONSE_POLICY
  AUTHORIZATION_OWNER

MONITORING_EVENTS:

  SOURCE_CHANGE
  DEPENDENCY_CHANGE
  CONFIGURATION_CHANGE
  MODEL_CHANGE
  BUILD_CHANGE
  SECURITY_ADVISORY
  TEST_FAILURE
  HASH_MISMATCH
  POLICY_VIOLATION
  EXPIRED_EVIDENCE
  OBSERVABILITY_FAILURE
  UNAUTHORIZED_OPERATION
  RISK_THRESHOLD_EXCEEDED

IMPACT_RESPONSE:

  Si el cambio no afecta una afirmación:
    Conservar la evidencia válida y justificarlo.

  Si afecta una afirmación:
    Invalidar la evidencia dependiente que corresponda.
    Ejecutar pruebas pertinentes.
    Determinar la necesidad de G23 y G24.

  Si compromete un invariante crítico:
    Suspender las operaciones afectadas.
    Preservar la evidencia.
    Ejecutar contención autorizada.
    Activar recuperación o rollback.

  Si se pierde la observabilidad obligatoria:
    Marcar el estado UNKNOWN.
    Aplicar la política FAIL_CLOSED.

MONITORING_LIMIT:

  El monitoreo sólo puede justificar afirmaciones
  dentro de su cobertura efectiva.

  Los sensores, la propia infraestructura de monitoreo
  y sus mecanismos de actualización también requieren
  evaluación y protección.

===============================================================================
19. CERTIFICACIÓN Y AUTORIZACIÓN
===============================================================================

READY_FOR_G24 es verdadero únicamente cuando:

  - El objeto está identificado.
  - El alcance está cerrado.
  - Los requisitos críticos están cubiertos.
  - La evidencia obligatoria está disponible.
  - Los controles canónicos aplicables están satisfechos.
  - Los controles PUAC requeridos están satisfechos.
  - No existen conflictos críticos impeditivos.
  - Los riesgos han recibido el tratamiento exigido.
  - G23 ha emitido una evaluación favorable válida.

G24 puede:

  APPROVE
  DENY
  RETURN_FOR_CORRECTION

Una aprobación debe generar un expediente firmado
o protegido por un mecanismo equivalente autorizado.

CERTIFICATE_CONTENT:

  certificate_id
  subject_id
  subject_version
  artifact_hash
  claims_certified[]
  claims_excluded[]
  assurance_profile
  evaluation_baseline
  evidence_digest
  g23_record
  g24_authority
  issuance_timestamp
  validity_conditions
  revocation_conditions
  supersession_reference

OPERATIONAL_AUTHORIZATION:

  Se concede separadamente de la emisión del certificado.

  Debe vincular certificado, entorno, permisos,
  responsable, límites de riesgo y monitoreo.

  No debe interpretarse como una autorización perpetua.

EXTERNAL_CERTIFICATION:

  Cualquier afirmación de conformidad con un esquema
  externo requiere el procedimiento y la autoridad
  exigidos por dicho esquema.

  El PUAC no crea certificados externos por declaración.

===============================================================================
20. FALLOS, CUARENTENA Y RECUPERACIÓN
===============================================================================

FAILURE_PIPELINE:

  DETECT
      ->
  RECORD
      ->
  DENY_AFFECTED_OPERATIONS
      ->
  PRESERVE_EVIDENCE
      ->
  IDENTIFY_LAST_VERIFIED_CHECKPOINT
      ->
  AUTHORIZE_REMEDIATION
      ->
  REPAIR_OR_ROLLBACK
      ->
  VERIFY_RESTORATION
      ->
  TEST_NON_REGRESSION
      ->
  UPDATE_ASSURANCE_CASE
      ->
  G23_IF_REQUIRED
      ->
  G24_IF_REQUIRED
      ->
  REAUTHORIZE_IF_PERMITTED
      ->
  CONTINUE_MONITORING

IF NO VERIFIED_CHECKPOINT:

  NO FALSE_ROLLBACK_DECLARATION.

  Mantener cuarentena.
  Registrar la imposibilidad.
  Escalar a la autoridad competente.
  Elaborar un nuevo plan de recuperación.

IF RESTORATION_FAILS:

  NO AUTOMATIC_ACTIVATION.

  Conservar el estado bloqueado.
  Registrar evidencia del fallo.
  Repetir el diagnóstico bajo autorización.

IF AN INCIDENT IS CLOSED:

  Debe existir evidencia de corrección,
  verificación, no regresión y autorización
  cuando corresponda.

===============================================================================
21. VERIFICACIÓN DE LA IMPLEMENTACIÓN DEL PUAC
===============================================================================

La propia implementación del PUAC debe someterse
a las reglas que establece.

MANDATORY_TEST_CLASSES:

  T01 — VALID_MANIFEST
  T02 — MALFORMED_MANIFEST
  T03 — DUPLICATE_IDENTIFIER
  T04 — CANONICAL_MUTATION_ATTEMPT
  T05 — UNAUTHORIZED_ACTION
  T06 — G23_BYPASS_ATTEMPT
  T07 — G24_BYPASS_ATTEMPT
  T08 — INSUFFICIENT_EVIDENCE
  T09 — CONFLICTING_EVIDENCE
  T10 — INVALID_HASH
  T11 — EXPIRED_AUTHORIZATION
  T12 — DEPENDENCY_CHANGE
  T13 — SECOND_ORDER_REGRESSION
  T14 — MONITORING_FAILURE
  T15 — INCIDENT_DETECTION
  T16 — RECOVERY_SUCCESS
  T17 — RECOVERY_FAILURE
  T18 — AUDIT_CHAIN_INTEGRITY
  T19 — CHRONOLOGICAL_CONFLICT
  T20 — EVIDENCE_INVALIDATION_PROPAGATION
  T21 — CROSS_DOMAIN_ISOLATION
  T22 — CERTIFICATION_SCOPE_MISMATCH
  T23 — INVALID_CERTIFICATE_REUSE
  T24 — INDEPENDENT_VALIDATOR_CONFLICT
  T25 — METACOGNITIVE_FALSE_POSITIVE
  T26 — METACOGNITIVE_FALSE_NEGATIVE
  T27 — ADVERSARIAL_INPUT
  T28 — HISTORICAL_RECORD_PRESERVATION

ACCEPTANCE:

  Toda prueba crítica obligatoria debe aprobarse.

  Toda falla debe conservar su evidencia.

  No se admiten resultados PASS producidos
  exclusivamente por declaraciones del mismo
  componente que se está evaluando.

  El estado CERTIFIED sólo puede asignarse
  después de G23 y G24 efectivos.

===============================================================================
22. GESTIÓN DE DEUDA HISTÓRICA
===============================================================================

El PUAC distingue entre:

  IDENTIFICADOR DECLARADO
  IDENTIFICADOR OBSERVADO
  DEFINICIÓN MATERIALIZADA
  REFERENCIA TEXTUAL
  REGISTRO REPETIDO
  IDENTIFICADOR FALTANTE

No son métricas intercambiables.

Cuando distintos documentos históricos afirmen
recuentos incompatibles, el expediente debe:

  - Conservar las cifras originales.
  - Identificar la metodología de cada recuento.
  - Delimitar el corpus evaluado.
  - Establecer si las unidades son comparables.
  - Registrar el resultado de un nuevo censo independiente.
  - Mantener los identificadores históricos intactos.

La normalización de métricas nunca autoriza
rellenar axiomas, renumerar bloques o modificar
material congelado sin autorización canónica.

Los estados históricos CERTIFIED, BLOCKED y PASS
se conservan atribuidos a su versión y ejecución.

Una declaración histórica de certificación
no prueba por sí sola la certificación efectiva
de una compilación actual.

===============================================================================
23. APLICACIÓN AL PROGRAMA MAESTRO DE LOUKSNA
===============================================================================

A0:
  Fuente canónica protegida.
  No se modifica durante la evaluación del PUAC.

A1:
  Requiere su propio expediente y certificación.

A2:
  Requiere su propio expediente y certificación.

A3:
  Requiere pruebas y certificación específicas
  de la integración entre A1 y A2.

A4:
  Requiere evaluación y certificación independientes
  dentro de su propia rama.

A5:
  Requiere evaluación de la integración autorizada
  entre A4, los motores validados y el adaptador
  de gobernanza correspondiente.

GLOBAL_SIZE_INVARIANT:

  SIZE(A3_OPERATIONAL_DISTRIBUTION) <= 479000000 BYTES

La verificación del límite debe incluir todos
los componentes obligatorios de la distribución.

No se permite excluir bytes operativos para
producir una certificación artificialmente favorable.

Los resultados de una rama no confieren
automáticamente certificación a otra.

===============================================================================
24. INCORPORACIÓN CANÓNICA
===============================================================================

ADMISSION_SEQUENCE:
  1. Conservar el archivo canónico de origen
     y su hash de referencia.

  2. Registrar el PUAC como candidato independiente.

  3. Verificar disponibilidad de los identificadores
     propuestos G25-G32.

  4. Construir la matriz de compatibilidad
     con todos los controles G01-G24.

  5. Ejecutar pruebas semánticas y estructurales.

  6. Resolver colisiones o contradicciones
     sin modificar silenciosamente el corpus histórico.

  7. Ejecutar validación independiente G23.

  8. Someter la incorporación a G24.

  9. Verificar la no regresión global.

 10. Demostrar el rollback correspondiente.

 11. Obtener autorización expresa de incorporación.

 12. Registrar la nueva versión y su procedencia.

SIN ESTA CADENA:

  STATUS = UNINCORPORATED
  CERTIFICATION = NOT_GRANTED
  ACTIVATION = FORBIDDEN

===============================================================================
25. INVARIANTE FINAL
===============================================================================

LA CERTIFICACIÓN ES UNA DECISIÓN FORMAL
SUSTENTADA EN EVIDENCIA.

EL ASEGURAMIENTO CONTINUO ES EL PROCESO
QUE CONSERVA, EXAMINA Y ACTUALIZA
LAS CONDICIONES QUE JUSTIFICAN ESA DECISIÓN.

LA METACOGNICIÓN EXAMINA LOS FUNDAMENTOS
DEL RAZONAMIENTO, PERO NO SUSTITUYE
LAS PRUEBAS NI LA AUTORIDAD.

LA LÓGICA FORMAL CONTROLA LOS INVARIANTES
QUE PUEDEN DEMOSTRARSE.

LA EVALUACIÓN EMPÍRICA CONTROLA LAS PROPIEDADES
QUE REQUIEREN OBSERVACIÓN Y EXPERIMENTACIÓN.

LA LÓGICA BINARIA DE AUTORIZACIÓN IMPIDE
EJECUTAR OPERACIONES CUANDO NO SE HAN
DEMOSTRADO SUS CONDICIONES OBLIGATORIAS.

LA PROCEDENCIA CONSERVA EL ORIGEN.
LA TRAZABILIDAD CONSERVA LAS RELACIONES.
LA AUDITABILIDAD CONSERVA LA HISTORIA.
LA GOBERNANZA CONSERVA LA AUTORIDAD.
G23 CONSERVA LA VALIDACIÓN INDEPENDIENTE.
G24 CONSERVA LA DECISIÓN DE CERTIFICACIÓN.
G25-G32, SI SON APROBADOS, AMPLÍAN EL ASEGURAMIENTO.

NINGUNO SUSTITUYE SILENCIOSAMENTE A OTRO.

FINAL_CONTRACT:

  DESIGN_FROM_CERTIFICATION_REQUIREMENTS = TRUE
  EVIDENCE_REQUIRED_FOR_CRITICAL_CLAIMS = TRUE
  INDEPENDENT_VALIDATION_REQUIRED = TRUE
  CERTIFICATION_AUTHORITY_REQUIRED = TRUE
  CONTINUOUS_ASSURANCE_REQUIRED = TRUE
  CONFLICT_PRESERVATION_REQUIRED = TRUE
  DETERMINISTIC_AUTHORIZATION_REQUIRED = TRUE
  NON_REGRESSION_REQUIRED = TRUE
  ROLLBACK_REQUIRED = TRUE
  NO_SILENT_CANONICAL_MUTATION = TRUE
  FAIL_CLOSED = TRUE

===============================================================================
FIN — PUAC 1.0.0
===============================================================================



## PARTE II: PUAC2 — ENMIENDAS ARQUITECTONICAS, SEMANTICAS Y ARITMETICAS

### 26. Naturaleza canónica y alcance independiente
PUAC2 es una extensión externa bajo la autoridad superior de Louksna.md. La preparación documental está autorizada por el usuario; incorporación canónica formal y certificación G23/G24 siguen la cadena definida en la sección 24 del original. Preservar B1–B134, AX0001–AX12414, cuatro agentes, catorce comandos, E01–E15, CFE001–CFE074, G01–G24 y DOC0001–DOC0022. No reasignar identidades ni transferir la autoridad del núcleo. Los ocho controles permanecen PUAC.C25–PUAC.C32; los IDs G25–G32 son propuestas no activadas.

### 27. D01 — Claim tipado y coherencia dimensional
El tipo Claim v2 incorpora obligatoriamente unit_of_measure, ya presente en CLAIM_KEY de la sección 04. La clave semántica es (subject_id, property_id, scope_id, context_id, version, validity_interval, unit_of_measure). claim_id es identidad del registro, no reemplazo de la clave semántica. Las unidades son tipadas y versionadas; magnitudes de dimensiones incompatibles no se comparan. Una cantidad adimensional debe declararse dimensionless y las exenciones not_applicable requieren fundamento. Toda conversión exige regla, unidad origen/destino, evidencia y preservación del valor original; no convertir por inferencia textual.

### 28. D02 — EventRecord y causalidad verificable
El tipo EventRecord v2 incorpora recorded_at_utc obligatorio. event_time_utc=ocurrencia declarada; observed_at_utc=detección; recorded_at_utc=persistencia real. sequence_number ordena eventos dentro del registro; causal_parents[] especifica dependencias causales. La precedencia temporal por sí sola no demuestra causalidad. Los relojes no confiables, recepciones tardías y rectificaciones dejan evidencia explícita; los ciclos causales se rechazan; los eventos previos permanecen inmutables.

### 29. D03 — AuthorityBinding y segregación
AuthorityBinding_V2 = (binding_id, actor_id, actor_identity_proof, role_id, issuer_id, issuer_authority_proof, action, object_id, scope_id, validity_interval, delegation_chain, revocation_state, provenance_id, signature_if_required).
PERMITIR una acción requiere identidad y delegación acreditadas, competencia para el objeto/alcance, ausencia de revocación y caducidad, y política de privilegio mínimo. Ante UNKNOWN, CONFLICT o autoevaluación presentada como independiente: DENY. CUSTOSZ V7 gobierna ejecución bajo autorización; su runtime y METAOS, cuando sea auténticamente disponible, son auxiliares técnicos; ninguno sustituye G23/G24.

### 30. D04 — RecoveryPlan y reversibilidad real
RecoveryPlan_V2 = (incident_id, authorized_actor, checkpoint_id, checkpoint_hash, target_environment, dependency_hashes[], restoration_oracles[], nonregression_plan, rollback_scope, irreversible_side_effects[], authority_ref).
Una copia cuyo hash coincide demuestra identidad de los bytes del snapshot, no restauración funcional del sistema completo ni reversión de efectos externos. CLOSED(incident) sólo si constan diagnóstico, corrección autorizada y ejecutada, verificación, no regresión, trazabilidad y G23/G24 cuando proceda. Si falta checkpoint verificado, cuarentena. Aun con restauración íntegra, reactivación requiere nueva autorización aplicable.

### 31. D05 y D07 — procedencia real y entorno
La fuente íntegra aportada por el usuario contiene 52.923 bytes, conservados en PUAC_1_0_0_ORIGINAL.txt y vinculados por SHA-256 en EXTENSION_MANIFEST.json. RUN_R6 era candidato derivado de extracto y se conserva intacto como evidencia histórica; su ausencia de original fue cierta en aquella ejecución, pero el original se recuperó para esta entrega. Su hash independiente de origen anterior al adjunto no está acreditado, por lo cual no se inventa un pedigree externo.
Las menciones de nueve familias nativas y nueve familias de routing corresponden al alcance de una misión histórica y NO son un defecto de las definiciones originales de PUAC. Se comprobarán mediante registros reales, hashes y manifiestos del runtime si se requieren. No presentar runtime.meta.observe como ejecución de un motor METAOS independiente sin evidencia verificable.

### 32. D06 — hermenéutica, metacognición y límites
Conservar G14, G15 y PUAC.MC.01–PUAC.MC.08, incluida la distinción TEXTO-OBSERVACION-CONTEXTO-INFERENCIA-INTERPRETACION-VALIDACION. La configuración teológica reformada declarada por Louksna se aplica donde corresponda, con control de eiségesis, proof-texting, anacronismo y falacias lexicales. Una fuente filológica apoya la interpretación pero no confiere autoridad canónica. La evidencia textual teológica no reemplaza la evidencia empírica exigida para afirmar funcionamiento de software; no inventar evaluaciones especializadas no ejecutadas.

### 33. D08–D10 — cobertura real y precisión histórica
Las dieciséis obligaciones INV-01–INV-16 y las veintiocho clases T01–T28 ya aparecen en el original. D08 diferencia definiciones, pruebas en un prototipo de referencia y pruebas operacionales contra el artefacto exacto. Los ensayos previos R3/R4 dieron 30 de 30 PASS sobre motor Python de referencia; esa evidencia es válida sólo en aquel alcance. D09: original YA separaba CertificationDecision de OperationalAuthorization y las respectivas proyecciones; PUAC2 endurece su vinculación por identidad, alcance, hash, vigencia y autoría. D10: el original YA contenía R5 y §20 para cierre de incidentes; PUAC2 formaliza el predicado verificable en vez de inventar una política inexistente.

### 34. Formalización aritmética exacta y deuda histórica
| Categoría | Cardinalidad declarada |
|---|---:|
| Bloques B1–B134 | 134 |
| Controles canónicos G01–G24 | 24 |
| Controles locales PUAC.C25–PUAC.C32 | 8 |
| Invariantes INV-01–INV-16 | 16 |
| Clases de prueba T01–T28 | 28 |
| Documentos congelados DOC0001–DOC0022 | 22 |
| Axiomas declarados AX0001–AX12414 | 12414 |
| Definiciones axiomáticas materializadas declaradas | 11757 |
| Deuda histórica declarada | 657 |
La igualdad 11757 + 657 = 12414 valida sólo la conciliación aritmética declarada, no acredita definición materializada de IDs faltantes. AX2415–AX12414 contiene 10000 posiciones contiguas (12414 − 2415 + 1); el subconjunto exacto de 657 ausencias en AX0001–AX2414 requiere censo material independiente; no inferir contigüidad ni completar huecos.
Para requisitos críticos R no vacío, cobertura_documental = |{r en R con contrato verificable}|/|R|. Cobertura_operacional = |{r en R con evidencia real suficiente, válida y aplicable}|/|R|; ambas se informan separadas. Si R es vacío, cobertura indefinida y requiere revisión de alcance. Para pruebas: T_operacional = n_tests_reales_aprobados/28. Para invariantes: I_operacional = n_invariantes_realmente_demostrados/16. Los PASS de referencia nunca entran en estos numeradores. Una cobertura de 1 no reemplaza G23/G24.
El límite A3 es SIZE(A3_OPERATIONAL_DISTRIBUTION) <= 479000000 bytes exactos, incluyendo cargas y metadatos obligatorios. 1 MB decimal = 1000000 bytes; 1 MiB binario = 1048576 bytes. Ninguna conversión ni redondeo autoriza descontar bytes reales.

### 35. Semántica de conflicto, evidencia y permisos
SUPPORTED, REFUTED, UNKNOWN y CONFLICT son estados del expediente probatorio y no sustituyen la máquina canónica DECLARED → EVIDENCED → VALIDATED → INDEPENDENTLY_VALIDATED → CERTIFIED → ACTIVE. CLAIM_KEY debe coincidir en sujeto, propiedad, contexto, alcance, versión, intervalo y unidad antes de declarar contradicción directa. No resolver discrepancias por último escritor ni similitud textual. PERMITIR si y sólo si todas las condiciones obligatorias están demostradas para la acción concreta; ante ausencia, UNKNOWN o CONFLICT, denegar y preservar evidencia. El éxito de una herramienta auxiliar no produce autoridad ni certificación heredada.

### 36. Controles complementarios y admisión
PUAC.C25=alcance/afirmaciones; PUAC.C26=evidencia/argumentación; PUAC.C27=independencia estructural; PUAC.C28=seguridad/riesgos; PUAC.C29=integridad/reproducibilidad; PUAC.C30=integración/no regresión; PUAC.C31=reversibilidad demostrada; PUAC.C32=vigencia/reevaluación. Cada uno conserva su identidad local hasta aprobación expresa de identificador y alcance; jamás sustituye G23 o G24.
Cadena: ESPECIFICACION → EVIDENCIA → VERIFICACION → G23 INDEPENDIENTE → G24 COMPETENTE → ADMISION_CANONICA_EXPRESA → AUTORIZACION_OPERACIONAL_SEPARADA SI CORRESPONDE. Cada transición registra actor, versión, hash, permisos y evidencia. Una certificación de componente no se propaga a integración ni una certificación arquitectónica acredita automáticamente código operacional.

### 37. Contrato final de PUAC2
PUAC2.md es el texto original íntegro más estas extensiones tipadas, aritméticas y semánticas. README.md expone el contraste intelectual verificable D01–D10 y las limitaciones de la entrega; EXTENSION_MANIFEST.json contiene hashes, ámbito y autoridad; los checkpoints y cadena de auditoría permiten reconstruir la generación. PUAC1.0 declaró NOT_CERTIFIED y PUAC2 no se etiqueta CERTIFIED sin G23 y G24 efectivamente concedidos. Louksna.md permanece intacto y gobierna la incorporación de una extensión canónica externa cuando su secuencia formal se cumpla.
