"""Proposed ledger rows for study L (ai2) with the exact 23-column header of docs/evidence.csv.

Ids (assigned by the lead): EML-44...69, PDT-43...52, CON-46...52, HAP-90...94.  Literature rows are sources opened in
this study (access level as opened; 'abstract only' where only the abstract was read); sources already in the ledger
are not repeated (Riviere 1998 ACT-08, Veluvolu 2013 ACT-11, Ibrahim 2021 ACT-14, Drotar 2016 PDT-28, Dragan &
Srinivasa 2013 HAP-23, Marchal-Crespo 2009 HAP-03, Kotani 2020 OPT-30, Character Trajectories CON-25, CMSIS-NN
EML-13).  Derived rows are this study's own SIMULATION or CALCULATION, filled from results/ai2/ai2.json at build time.
The lead merges them; docs/evidence.csv is not edited here.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional

from . import REPO_ROOT

R1, R2 = "2026-09-28", "2026-09-29"
TRANSFER = ("Simulation on synthetic glyph writers, synthetic tremor and assumed hand, grip, sensor and device parameters "
            "(model HW1); not a measurement")


def header() -> List[str]:
    with open(REPO_ROOT / "docs" / "evidence.csv", newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


def L(id_, topic, citation, year, doi, stype, eclass, access, setup, parts, comp, finding, units, locator, limits, relevance,
      transfer, treason, implication, retrieved, query, stream) -> Dict[str, str]:
    return {"id": id_, "topic": topic, "citation": citation, "year": year, "doi_or_url": doi, "source_type": stype,
            "evidence_class": eclass, "access_level": access, "task_or_setup": setup, "participants_or_bench": parts,
            "comparator": comp, "key_quantitative_findings": finding, "units_and_conditions": units, "locator": locator,
            "limitations": limits, "relevance_to_design": relevance, "transferability": transfer,
            "transferability_reason": treason, "design_implication": implication, "retrieved": retrieved,
            "search_query": query, "stream": stream, "lead_verification": ""}


ARXIV = "arXiv API export.arxiv.org/api/query?id_list="
EUTILS = "NCBI E-utilities efetch (PubMed abstract)"


def literature() -> List[Dict[str, str]]:
    return [
        L("EML-44", "Tremor estimation: two-stage voluntary/tremor separation with WFLC and Kalman filtering (gyroscopes)",
          "Gallego JA, Rocon E, Roa JO, Moreno JC, Pons JL. Real-time estimation of pathological tremor parameters from gyroscope data. Sensors 10(3):2129-2149",
          "2010", "10.3390/s100302129 ; PMID 22294919 ; PMC3264472", "journal", "physical human study", "abstract only",
          "Upper-limb gyroscopes; stage 1 separates voluntary and tremorous motion by frequency content, stage 2 estimates instantaneous tremor amplitude and frequency (WFLC-type LMS with a Kalman filter)",
          "People with pathological tremor (numbers not in the abstract)", "Estimator variants within the paper",
          "Real-time two-stage scheme; quantitative accuracy not read (abstract only)", "n/a (abstract)", "Abstract",
          "Abstract only; wrist/forearm gyroscopes, not a pen", "The model-based stack here is the same two-stage idea: a tremor-line detector/gate then a Kalman estimate of the oscillation",
          "medium", "Pathological tremor, but limb segments and gyroscopes rather than a pen tip",
          "Keep an explicit tremor-line stage in front of the estimator; it is what keeps tremor-free writing untouched in this study", R1,
          EUTILS + " PMID 22294919", "EML"),
        L("EML-45", "Kalman-network hybrid (learned Kalman gain)",
          "Revach G, Shlezinger N, Ni X, Escoriza AL, van Sloun RJG, Eldar YC. KalmanNet: neural network aided Kalman filtering for partially known dynamics. IEEE Trans Signal Process 70:1532-1547",
          "2022", "arXiv:2107.10043", "journal", "numerical simulation", "abstract only",
          "Kalman filter structure kept; the gain computed by a recurrent network trained from data", "Synthetic and benchmark state-space models",
          "Model-based Kalman/EKF with full or mismatched knowledge", "Learns from data with partial model knowledge and copes with mismatch; numbers not read (abstract only)",
          "n/a (abstract)", "arXiv abstract", "Abstract only; not tremor", "Precedent for the hybrid estimator here (network correction on top of the Kalman/RTS estimate)",
          "medium", "General estimation method; the pen's model mismatch (grip, friction) is the use case", "A hybrid keeps the physics estimate as a fallback and lets the network learn only the residual", R1,
          ARXIV + "2107.10043", "EML"),
        L("EML-46", "Temporal convolutional networks for sequence modelling",
          "Bai S, Kolter JZ, Koltun V. An empirical evaluation of generic convolutional and recurrent networks for sequence modeling. arXiv:1803.01271",
          "2018", "arXiv:1803.01271", "preprint", "numerical simulation", "abstract only",
          "Causal dilated convolutions (TCN) compared with LSTM/GRU on standard sequence benchmarks", "Benchmark datasets", "Canonical recurrent networks",
          "A simple TCN outperforms canonical recurrent networks across a diverse range of tasks and shows longer effective memory (abstract)",
          "n/a (abstract)", "arXiv abstract", "Abstract only; benchmarks are not tremor", "Architecture of the causal learned estimators here (dilations 1-128 at 500 Hz, about 1 s receptive field)",
          "medium", "Generic method", "A causal TCN of about 34 k parameters is the reference learned estimator", R1, ARXIV + "1803.01271", "EML"),
        L("EML-47", "Fixed-lag smoothing: RTS backward recursion with stored gains",
          "Sarkka S. Bayesian Filtering and Smoothing. Cambridge University Press (IMS Textbooks 3), s10.5 General fixed-lag smoother equations, Algorithm 10.7",
          "2013", "https://users.aalto.fi/~ssarkka/pub/cup_book_online_20131111.pdf", "book", "analytical derivation", "full text",
          "Gaussian fixed-lag smoother: store the filter's smoothing gains during prediction, then per time step run the RTS backward recursion over the lag window",
          "n/a (method)", "Recursive fixed-lag form (Rauch 1963, Meditch 1969); augmented-state form (Moore 1973)",
          "'Fixed-lag smoothing can be considered as optimal filtering, where a constant delay is tolerated in the estimates'; computations per step grow linearly with the lag; the recursive fixed-lag form 'has been shown (Kelly and Anderson, 1971) ... numerically unstable'",
          "n/a", "s10.5, Algorithm 10.7, pp. 162-164 (online PDF)", "Method text; no tremor application",
          "Exactly the delayed-ink estimator implemented here (forward Kalman over merged IMU/page events, stored gains, backward pass per output)",
          "high", "Standard estimation theory; the pen needs only the linear-Gaussian case", "Use the stored-gain RTS form on the pen MCU; cost grows with the lag (bounded here to 100 ms)", R2,
          "curl users.aalto.fi/~ssarkka/pub/cup_book_online_20131111.pdf; pdftotext; grep fixed-lag", "EML"),
        L("EML-48", "Transformer position method for sliding windows (ALiBi)",
          "Press O, Smith NA, Lewis M. Train short, test long: attention with linear biases enables input length extrapolation. ICLR 2022; arXiv:2108.12409",
          "2022", "arXiv:2108.12409", "conference", "numerical simulation", "abstract only",
          "Query-key attention scores biased by a penalty proportional to distance; no positional embeddings", "Language modelling benchmarks",
          "Sinusoidal and other position methods", "A 1.3 B-parameter model trained on 1024-token inputs extrapolates to 2048 with the same perplexity as a sinusoidal model trained on 2048 (abstract)",
          "perplexity", "arXiv abstract", "Abstract only; language, not sensor streams", "Lets the small causal transformer here run on a sliding window of sensor data",
          "medium", "Generic method", "Use distance biases, not absolute positions, for streaming sensor transformers", R2, ARXIV + "2108.12409", "EML"),
        L("EML-49", "Proximal policy optimisation (PPO)",
          "Schulman J, Wolski F, Dhariwal P, Radford A, Klimov O. Proximal policy optimization algorithms. arXiv:1707.06347",
          "2017", "arXiv:1707.06347", "preprint", "numerical simulation", "abstract only",
          "Policy-gradient method alternating sampling and several epochs of minibatch updates of a clipped surrogate objective", "Simulated robotic locomotion and Atari",
          "Other online policy-gradient methods", "Better overall than other online policy-gradient methods on the benchmarks, simpler than TRPO (abstract)",
          "n/a (abstract)", "arXiv abstract", "Abstract only", "Algorithm of the arbiter and residual policies here (Stable-Baselines3 2.9)",
          "medium", "Generic method", "PPO is the default on-policy algorithm for the pen's shared-control policies", R1, ARXIV + "1707.06347", "EML"),
        L("EML-50", "Soft actor-critic (SAC)",
          "Haarnoja T, Zhou A, Abbeel P, Levine S. Soft actor-critic: off-policy maximum entropy deep reinforcement learning with a stochastic actor. ICML 2018; arXiv:1801.01290",
          "2018", "arXiv:1801.01290", "conference", "numerical simulation", "abstract only",
          "Off-policy actor-critic in the maximum-entropy framework", "Continuous-control benchmarks", "On- and off-policy methods",
          "State-of-the-art performance on continuous-control benchmarks and stable across random seeds (abstract)", "n/a (abstract)", "arXiv abstract",
          "Abstract only", "Second algorithm for the arbiter here (sample-efficient comparison with PPO)", "medium", "Generic method",
          "Compare an off-policy method under the same data budget before choosing", R1, ARXIV + "1801.01290", "EML"),
        L("EML-51", "Domain randomisation for sim-to-real transfer",
          "Tobin J, Fong R, Ray A, Schneider J, Zaremba W, Abbeel P. Domain randomization for transferring deep neural networks from simulation to the real world. IROS 2017; arXiv:1703.06907",
          "2017", "arXiv:1703.06907", "conference", "physical bench experiment", "abstract only",
          "Object detectors trained only on randomised simulated images, tested on real images and a real grasping task", "Robot grasping in clutter",
          "n/a", "Real-world localisation accurate to 1.5 cm from simulated training only (abstract)", "cm", "arXiv abstract",
          "Abstract only; vision, not tremor", "The learned estimators and policies here train on writers, tremor, grip and sensor noise drawn from wide ranges",
          "medium", "Transfer principle, different modality", "Randomise every parameter the pen cannot know (grip, tremor, sensor noise) and test on held-out writers", R1,
          ARXIV + "1703.06907", "EML"),
        L("EML-52", "Dynamics randomisation for sim-to-real control",
          "Peng XB, Andrychowicz M, Zaremba W, Abbeel P. Sim-to-real transfer of robotic control with dynamics randomization. ICRA 2018; arXiv:1710.06537",
          "2018", "arXiv:1710.06537", "conference", "physical bench experiment", "abstract only",
          "Policies trained in simulation with randomised dynamics, deployed on a real robot arm (object pushing)", "Fetch robot arm", "Policies without randomisation",
          "Policies trained with randomised dynamics transfer to the real robot without real-world training (abstract; numbers not read)", "n/a (abstract)",
          "arXiv abstract", "Abstract only", "Dynamics randomisation of hand, grip and tremor in the training data here", "medium", "Different plant",
          "Randomise the grip and hand dynamics, not only the tremor", R1, ARXIV + "1710.06537", "EML"),
        L("EML-53", "RL controller trained only in simulation, transferred to people (exoskeleton)",
          "Luo S, Jiang M, Zhang S, Zhu J, Yu S, Dominguez Silva I, Wang T, Rouse E, Zhou B, Yuk H, Zhou X, Su H. Experiment-free exoskeleton assistance via learning in simulation. Nature 630:353-359",
          "2024", "10.1038/s41586-024-07382-4 ; PMID 38867127", "journal", "physical human study", "abstract only",
          "Musculoskeletal and exoskeleton simulation, RL controller, no human-in-the-loop tuning; tested in people", "People walking, running and climbing stairs (number not in the abstract read)",
          "No exoskeleton", "Metabolic rate reduced 24.3 % walking, 13.1 % running, 15.4 % stair climbing (abstract)", "% metabolic rate", "Abstract",
          "Abstract only; hip exoskeleton, not tremor", "Precedent that simulation-trained assistive policies can transfer when the simulator carries the human",
          "low", "Different device and objective", "The pen's RL policies need a human-hand simulator with the same care (sim2/MyoSuite) before any transfer claim", R1,
          EUTILS + " PMID 38867127", "EML"),
        L("EML-54", "Residual reinforcement learning on top of a conventional controller",
          "Johannink T, Bahl S, Nair A, Luo J, Kumar A, Loskyll M, Ojea JA, Solowjow E, Levine S. Residual reinforcement learning for robot control. ICRA 2019; arXiv:1812.03201",
          "2019", "arXiv:1812.03201", "conference", "physical bench experiment", "abstract only",
          "Control split into a conventional feedback part and a residual learned with RL, for contact and friction problems", "Robot assembly (real and simulated)",
          "Conventional controller alone; RL alone", "Residual RL solves contact-rich tasks that the conventional controller handles poorly (abstract; numbers not read)",
          "n/a (abstract)", "arXiv abstract", "Abstract only", "The residual policy here adds a bounded correction to the model-based tremor estimate",
          "medium", "Different task", "Learn only the correction; keep the model-based estimate as the safe base", R2, ARXIV + "1812.03201", "EML"),
        L("EML-55", "Residual policy learning",
          "Silver T, Allen K, Tenenbaum J, Kaelbling L. Residual policy learning. arXiv:1812.06298",
          "2018", "arXiv:1812.06298", "preprint", "numerical simulation", "abstract only",
          "Residual on top of hand-designed or model-predictive controllers; six MuJoCo manipulation tasks with partial observability, sensor noise, misspecification and miscalibration",
          "Simulated manipulation", "RL from scratch; the initial controller", "RPL improves imperfect controllers and succeeds where RL alone is data-inefficient or fails (abstract)",
          "n/a (abstract)", "arXiv abstract", "Abstract only; simulation only", "As EML-54", "medium", "Different task",
          "Residual learning is the data-efficient way to add RL to the pen", R2, ARXIV + "1812.06298", "EML"),
        L("EML-56", "Shared autonomy with deep RL (human-in-the-loop)",
          "Reddy S, Dragan AD, Levine S. Shared autonomy via deep reinforcement learning. RSS 2018; arXiv:1802.01744",
          "2018", "arXiv:1802.01744", "conference", "physical human study", "abstract only",
          "Model-free deep RL co-pilot that blends the user's input with its own action, without a model of the user's goal", "12 users (game), 4 users (real quadrotor) per the abstract",
          "User alone", "The co-pilot improved task performance in the user studies (abstract; effect sizes not read)", "n/a (abstract)", "arXiv abstract",
          "Abstract only; small samples", "Learned arbitration is a studied alternative to hand-tuned blending", "medium", "Different task and input device",
          "An RL arbiter must be judged by task success and by the user's sense of control", R1, ARXIV + "1802.01744", "EML"),
        L("EML-57", "Shared autonomy by hindsight optimisation (assistance under goal uncertainty)",
          "Javdani S, Srinivasa SS, Bagnell JA. Shared autonomy via hindsight optimization. RSS 2015; arXiv:1503.07619 ; Javdani S, Admoni H, Pellegrinelli S, Srinivasa SS, Bagnell JA. Shared autonomy via hindsight optimization for teleoperation and teaming. IJRR 2018; arXiv:1706.00155",
          "2015; 2018", "arXiv:1503.07619 ; arXiv:1706.00155", "conference; journal", "physical human study", "abstract only",
          "POMDP over the user's goal with maximum-entropy inverse optimal control; assistance toward all likely goals before the goal is known",
          "User studies (numbers not read)", "Predict-then-blend and no assistance",
          "Users completed tasks faster with less input and less idling; ratings mixed between control authority and speed (abstracts)", "n/a (abstract)",
          "arXiv abstracts", "Abstracts only", "How the pen can help before it is sure which letter is coming (assist toward the set of likely letters)",
          "medium", "Teleoperation, not writing", "Blend by confidence over candidate letters, and expect some users to prefer authority over speed", R1,
          ARXIV + "1503.07619,1706.00155", "EML"),
        L("EML-58", "Shared control in physical HRI: intent detection, arbitration, communication (review)",
          "Losey DP, McDonald CG, Battaglia E, O'Malley MK. A review of intent detection, arbitration, and communication aspects of shared control for physical human-robot interaction. Appl Mech Rev 70(1):010804",
          "2018", "10.1115/1.4039145 ; https://collab.me.vt.edu/pdfs/losey_amr2018.pdf", "journal", "review", "full text",
          "Review organised by intent detection, arbitration (division of control; static vs dynamic roles) and feedback/communication", "n/a (review)", "n/a",
          "Arbitration treated as a knob between human and robot control; case studies in rehabilitation robots and prostheses (qualitative review)", "n/a",
          "Sections 3 (arbitration) and 5 (case studies)", "Qualitative", "Frames the pen's arbitration function (how much to help, when to hand back) and the need to tell the user who is in control",
          "medium", "Physical HRI review; pens not covered", "Specify the arbitration law and the user-facing cue together", R1, "curl collab.me.vt.edu/pdfs/losey_amr2018.pdf; pdftotext", "EML"),
        L("EML-59", "Assist-as-needed robotic assistance (force decay when errors are small)",
          "Wolbrecht ET, Chan V, Reinkensmeyer DJ, Bobrow JE. Optimizing compliant, model-based robotic assistance to promote neurorehabilitation. IEEE Trans Neural Syst Rehabil Eng 16(3):286-297",
          "2008", "10.1109/TNSRE.2008.918389 ; PMID 18586608", "journal", "physical human study", "abstract only",
          "Adaptive model-based assistance with a force-decay term when tracking errors are small (Pneu-WREX, stroke)", "People after stroke (number not in the abstract read)",
          "Assistance without decay", "Decay term reduces assistance when errors are small and counters 'slacking' (patients letting the robot do the work) (abstract)",
          "n/a (abstract)", "Abstract", "Abstract only; arm robot", "Basis of the per-letter assistance-as-needed gain law here", "medium", "Arm rehabilitation, not writing",
          "Let help decay when the writer does well, or the writer may slack", R1, EUTILS + " PMID 18586608", "EML"),
        L("EML-60", "Handwriting synthesis with recurrent networks (mixture density outputs)",
          "Graves A. Generating sequences with recurrent neural networks. arXiv:1308.0850",
          "2013", "arXiv:1308.0850", "preprint", "numerical simulation", "abstract only",
          "LSTM with mixture density outputs; online handwriting synthesis conditioned on text", "IAM-OnDB (per the paper; abstract read)", "n/a",
          "Generates realistic cursive handwriting in a wide variety of styles (abstract)", "n/a (abstract)", "arXiv abstract",
          "Abstract only; needs a licensed online-handwriting corpus to train", "The learned route for writing in the user's style; not trainable here without a downloadable licensed corpus with time stamps",
          "medium", "Method; data licence is the constraint", "Keep sigma-lognormal synthesis for few-sample style; a learned generator needs licensed pen-trajectory data", R1, ARXIV + "1308.0850", "EML"),
        L("EML-61", "Handwriting generation with disentangled content and style",
          "Aksan E, Pece F, Hilliges O. DeepWriting: making digital ink editable via deep generative modeling. CHI 2018; arXiv:1801.08379",
          "2018", "arXiv:1801.08379", "conference", "numerical simulation", "abstract only",
          "Conditional variational RNN separating content and style of digital ink; editing and synthesis in the user's style", "Collected handwriting dataset (per the abstract)",
          "n/a", "Synthesis of editable ink in the writer's style (abstract; quantitative results not read)", "n/a (abstract)", "arXiv abstract", "Abstract only",
          "Style-preserving synthesis for autowrite and the app's clean copy", "medium", "Method", "A learned style model is the upgrade path once licensed data exist", R1, ARXIV + "1801.08379", "EML"),
        L("EML-62", "Handwriting generation with diffusion models",
          "Luhman T, Luhman E. Diffusion models for handwriting generation. arXiv:2011.06704",
          "2020", "arXiv:2011.06704", "preprint", "numerical simulation", "abstract only",
          "Diffusion probabilistic model generating handwriting strokes with style from image samples", "IAM-OnDB (per the abstract)", "n/a",
          "Realistic handwriting from a diffusion model without adversarial training or text alignment (abstract)", "n/a (abstract)", "arXiv abstract", "Abstract only",
          "Another learned route to style synthesis", "low", "Compute and data far above the pen's", "Not for the pen; possibly for the phone app", R1, ARXIV + "2011.06704", "EML"),
        L("EML-63", "Word prediction in AAC: communication rate and keystroke savings",
          "Trnka K, Yarrington D, McCaw J, McCoy KF, Pennington C. The effects of word prediction on communication rate for AAC. NAACL-HLT 2007 Companion, pp 173-176",
          "2007", "https://aclanthology.org/N07-2044", "conference", "physical human study", "full text",
          "Copying Switchboard excerpts with an AAC interface: advanced (n-gram) prediction, basic prediction, none", "17 adults (pseudo-impaired: slowed input)",
          "Basic prediction and no prediction", "8.09 wpm advanced vs 5.50 basic vs 5.06 none; keystroke savings 50.3 % vs 18.2 % (potential 55.2 vs 25.0 %); prediction utilisation 90.9 vs 73.3 %; advanced 44.4 % faster than basic",
          "words per minute; %", "Table 1; s3", "Able-bodied, simulated slow input; typing not handwriting", "Word prediction helps when predictions are good enough to be used",
          "medium", "Different input channel; same prediction principle", "Offer the next word only when its quality is high; a weak predictor adds cost", R1, "aclanthology.org/N07-2044.pdf; pdftotext", "EML"),
        L("EML-64", "AAC language model data: crowdsourced messages select better training text",
          "Vertanen K, Kristensson PO. The imagination of crowds: conversational AAC language modeling using crowdsourcing and large data sources. EMNLP 2011, pp 700-711",
          "2011", "https://aclanthology.org/D11-1065", "conference", "calculation", "full text",
          "5890 crowdsourced AAC-like messages used to select Twitter, blog and Usenet sentences for training", "Text corpora",
          "Model trained on telephone transcripts", "Perplexity cut 60-82 % relative on three AAC-like test sets; potential keystroke savings +5-11 %", "perplexity; %",
          "Abstract; s4-5", "Text-entry simulation, no users", "The training text must match what people write (notes, messages), not only example sentences",
          "medium", "Language-model data selection transfers to handwriting prediction", "Train the pen's predictor on note-like text; measure on the user's own notes", R1, "aclanthology.org/D11-1065.pdf; pdftotext", "EML"),
        L("EML-65", "Public-domain sentence text for language models (Common Voice sentence collector and Wikipedia sentences)",
          "Mozilla Common Voice. server/data/en/sentence-collector.txt and wiki.en.txt; README 'Licensing and content source'",
          "2024", "https://github.com/common-voice/common-voice (server/data/en)", "documentation", "manufacturer statement", "full text",
          "Sentence text released for voice recording", "n/a (text corpus)", "n/a",
          "README: sentence text in /server/data comes from the Sentence Collector or the Wikipedia extractor and is released under CC0 (europarl files excluded here); files used: sentence-collector.txt and wiki.en.txt (85,658,274 bytes)",
          "sentences", "README; files as downloaded (sha256 recorded in ai2/textpred.py outputs)", "Short read-aloud sentences, not notes",
          "A larger CC0 corpus for the pen's word and letter predictor", "high", "Licence stated by the publisher", "Usable for training the shipped predictor without licence risk", R1,
          "curl raw.githubusercontent.com/common-voice/common-voice/main/server/data/en/", "EML"),
        L("HAP-90", "Perception of inking latency (stylus, direct display)",
          "Annett M, Ng A, Dietz P, Bischof WF, Gupta A. How low should we go? Understanding the perception of latency while inking. Graphics Interface 2014, pp 167-174",
          "2014", "https://webdocs.cs.ualberta.ca/~wfb/publications/C-2014-GI-Latency.pdf ; https://graphicsinterface.org/proceedings/gi2014/gi2014-22/", "conference", "physical human study", "full text",
          "High-performance stylus system (about 1 ms base latency); JND against a 7 ms baseline while drawing a line, writing 'party' and drawing a star (Exp 1); nib-ink offsets and hand visibility (Exp 2)",
          "Exp 1: 12 adults; Exp 2: 12 adults", "7 ms baseline latency",
          "JND median 53 ms line (range 31-76), 50 ms writing 'party' (32-87), 61 ms star (21-82), 53 ms over tasks (task n.s.); Exp 2: hand and stylus visible Mdn 59 ms (33-104) vs hidden 97 ms (59-105), p < 0.005; displayed ink offsets 0/6.5/65 mm had no significant effect; commercial devices 60-120 ms",
          "ms of stylus-to-ink latency", "s4.5 Results (Exp 1); s5 Results (Exp 2); Figures 3 and 5", "Tablet display, not paper; n = 12 per experiment",
          "What a writer sees with delayed ink: the hand and pen move ahead and the ink follows; about half of writers notice 50 ms", "medium",
          "Same perceptual question (ink trailing the pen), different surface", "Keep the ink lag at or below about 25-50 ms; treat 100 ms as noticeable by nearly everyone", R1,
          "curl webdocs.cs.ualberta.ca/~wfb/publications/C-2014-GI-Latency.pdf; pdftotext", "HAP"),
        L("HAP-91", "Delayed visual feedback in handwriting: stroke duplication errors",
          "Tamada T. Effects of delayed visual feedback on handwriting. Japanese Psychological Research 37(2):103-109",
          "1995", "10.4992/psycholres1954.37.103 ; https://www.jstage.jst.go.jp/article/psycholres1954/37/2/37_2_103/_article", "journal", "physical human study", "abstract only",
          "Handwriting with visual feedback delayed 0, 33, 67, 100, 133, 167, 267 and 500 ms", "Participants (number not in the abstract read)", "0 ms",
          "Error rates rose with delay; addition errors (stroke duplication, 'feeeling'), where a set of strokes repeats; visual monitoring indispensable for repetitive letters (abstract)",
          "ms delay; error rate", "J-STAGE abstract", "Abstract only; whole visual scene delayed (video), not ink alone",
          "A lagging ink could cause repeated strokes and letters in writers who rely on seeing their ink (m, n, u, w, e)",
          "medium", "Delay of the whole visual feedback, not of ink behind a visible hand", "Test delayed ink for letter duplication errors (EXP-L02)", R1, "J-STAGE article page (abstract)", "HAP"),
        L("HAP-92", "Delayed visual feedback in handwriting (Kanji and English)",
          "Morikiyo Y, Matsushima T. Effects of delayed visual feedback on motor control performance. Perceptual and Motor Skills 70(1):111-114",
          "1990", "10.2466/pms.1990.70.1.111 ; PMID 2326107", "journal", "physical human study", "abstract only",
          "Writing Kanji and English with visual feedback delayed 200, 500, 767 and 1000 ms", "Participants (number not read)", "No delay",
          "Large decrement with delay; errors were insertion of line elements and letter duplication; letter size increased with delay (abstract)", "ms", "Abstract",
          "Abstract only; delays of 200 ms and more", "Upper bound: at 200 ms and above handwriting breaks down", "medium", "Whole-scene video delay",
          "Never let the ink lag exceed 100 ms", R1, EUTILS + " PMID 2326107", "HAP"),
        L("HAP-93", "Delayed visual feedback on visual-motor tasks (early study)",
          "Smith WM, McCrary JW, Smith KU. Delayed visual feedback and behavior. Science 132(3433):1013-1014",
          "1960", "10.1126/science.132.3433.1013 ; PMID 17820673", "journal", "physical human study", "abstract only",
          "Video-tape delay of visual feedback during simple visual-motor tasks", "Participants (not read)", "No delay",
          "Effects 'marked and deleterious', similar to delayed auditory feedback (abstract; delay value not in the abstract)", "n/a", "Abstract",
          "Abstract only", "Historical basis for the risk of lagged visual feedback", "low", "Old video method; delay not stated in the abstract",
          "Supports measuring writers' errors under ink lag rather than assuming adaptation", R1, EUTILS + " PMID 17820673", "HAP"),
        L("HAP-94", "Assist-as-needed with a forgetting factor and an error deadband (optimisation of error and assistance)",
          "Emken JL, Benitez R, Reinkensmeyer DJ. Human-robot cooperative movement training: learning a novel sensory motor transformation during walking with robotic assistance-as-needed. J Neuroeng Rehabil 4:8",
          "2007", "10.1186/1743-0003-4-8 ; PMID 17391527 ; PMC1847825", "journal", "physical human study", "abstract only",
          "Robotic force-field 'virtual impairment' on the left leg during treadmill walking; AAN trainer derived from minimising error plus assistance",
          "10 unimpaired adults", "Without the error-weighting function",
          "Optimal trainer = error-based controller with a forgetting factor; an error weighting (deadband) lets assistance fade to zero despite natural variability; 'the robot must relax its assistance at a rate faster than that of the learning human' (abstract)",
          "n/a (abstract)", "Abstract", "Abstract only; unimpaired walkers", "Exact form of the per-letter guidance gain law here: g(k+1) = f g(k) + kappa (e(k) - e_tol)+",
          "medium", "Different limb and task; same learning principle", "Use a forgetting factor f < 1 and a tolerance band so help fades; fade faster than the writer learns", R2,
          EUTILS + " PMID 17391527", "HAP"),
        L("CON-46", "Kinematic theory of rapid movements: lognormal velocity profiles",
          "Plamondon R. A kinematic theory of rapid human movements. Part I: movement representation and generation. Biological Cybernetics 72(4):295-307",
          "1995", "10.1007/BF00202785 ; PMID 7748959", "journal", "analytical derivation", "abstract only",
          "Neuromuscular network impulse response is lognormal (central limit theorem over coupled subsystems); delta-lognormal law", "n/a (theory)", "Other velocity-profile models",
          "Lognormal impulse response; the delta-lognormal law reproduces rapid-movement velocity profiles (abstract)", "n/a", "Abstract", "Abstract only",
          "Basis of the sigma-lognormal extraction and synthesis here", "high", "Handwriting kinematics theory", "Represent the user's letters as lognormal strokes for synthesis from few samples", R1,
          EUTILS + " PMID 7748959", "CON"),
        L("CON-47", "Sigma-lognormal extraction: iDeLog",
          "Ferrer MA, Diaz M, Carmona-Duarte C, Plamondon R. iDeLog: iterative dual spatial and kinematic extraction of sigma-lognormal parameters. IEEE TPAMI 42(1):114-125",
          "2020", "10.1109/TPAMI.2018.2879312 ; PMID 30403620", "journal", "numerical simulation", "abstract only",
          "Two-step extraction: virtual target points and angles from the trajectory, lognormals from the velocity; iterative refinement", "Handwriting databases (per the abstract)",
          "Earlier extractors", "Better reconstruction than earlier extractors (abstract; numbers not read)", "n/a (abstract)", "Abstract", "Abstract only",
          "Extraction method family used here (a simpler least-squares variant)", "medium", "Method", "Extraction quality sets the style fidelity of synthesis", R1,
          EUTILS + " PMID 30403620", "CON"),
        L("CON-48", "Real handwriting shapes from 60 writers (UJI Pen Characters v2)",
          "Prat F, Castro M, Llorens D, Marzal A, Vilar J. UJI Pen Characters (Version 2) [dataset]. UCI Machine Learning Repository (donated 2009); Llorens et al., LREC 2008",
          "2009", "https://archive.ics.uci.edu/dataset/177/uji+pen+characters+version+2", "dataset", "physical human study", "full text",
          "Isolated characters written on a Toshiba Portege M400 tablet PC; x/y points per stroke, no time stamps", "60 writers (40 train, 20 test), 11,640 samples, 97 classes",
          "n/a", "11,640 samples, 97 character classes; licence CC BY 4.0 (dataset page)", "tablet units (100 per mm assumed in ai2/stage_synth.py)", "UCI dataset page",
          "Shapes only (no time stamps), tablet not paper", "The only licensed multi-writer real handwriting used here (learned few-shot style generator, task 5)",
          "medium", "Real writers, isolated letters, tablet", "Enough to test style transfer of shapes; not enough for kinematics", R1, "archive.ics.uci.edu/dataset/177 (page) and static/public/177 zip", "CON"),
        L("PDT-43", "Deep RL for tremor suppression in simulation (soft exoskeleton, PD)",
          "Endrei T, Foldi S, Makk A, Cserey G. Learning to suppress tremors: a deep reinforcement learning-enabled soft exoskeleton for Parkinson's patients. Front Robot AI 12:1537470",
          "2025", "10.3389/frobt.2025.1537470 ; PMID 40469913 ; PMC12133501", "journal", "numerical simulation", "full text (PMC)",
          "PyBullet + Gym arm model (7 DoF); tremor = two sines + noise; TD7 agent; domain randomisation 4-12 Hz, amplitude 0.1-1.0, anatomy 0.9-1.1x",
          "Simulation only", "Uncontrolled simulated arm", "More than 99 % tremor amplitude suppression in simulation; the observation includes the tremor torques; no sim-to-real test",
          "% tremor amplitude", "Methods; Results", "Privileged observation (tremor torques) and simulation only",
          "Shows how easily RL results look perfect when the policy observes the tremor; the policies here see only the pen's sensors", "low",
          "Privileged observations; no hardware", "Report RL only with the sensors the pen has, on held-out writers and seeds", R1, "Europe PMC full text PMC12133501", "PDT"),
        L("PDT-44", "ET spiral analysis: tremor from tablet pen positions (clinical validation)",
          "Haubenberger D, Kalowitz D, Nahab FB, Toro C, Ippolito D, Luckenbaugh DA, Wittevrongel L, Hallett M. Validation of digital spiral analysis as outcome parameter for clinical trials in essential tremor. Mov Disord 26(11):2073-2080",
          "2011", "10.1002/mds.23808 ; PMID 21714004", "journal", "physical human study", "abstract only",
          "Digitising-tablet spirals; tremor severity from the velocity-spectrum tremor peak (FFT of pen-tip positions); ethanol challenge", "9 ET patients, 54 spirals",
          "Visual ratings", "Correlated with visual ratings (P < 0.0001) and more sensitive to the ethanol effect (P < 0.05) (abstract)", "spectral peak amplitude", "Abstract",
          "Abstract only; small n", "Supports a tremor-line (spectral peak) detector on pen-tip data as the pen's gate", "medium", "ET, tablet pen tip",
          "The pen can calibrate and log tremor from its own page sensor in the same way", R1, EUTILS + " PMID 21714004", "PDT"),
    ]


# ------------------------------------------------------------------ derived rows (filled from ai2.json)
def _g(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict) or k not in d or d[k] is None:
            return default
        d = d[k]
    return d


def _f(x, fmt="{:.0f}"):
    try:
        return "n/a" if x is None else fmt.format(x)
    except (TypeError, ValueError):
        return "n/a"


def D(id_, topic, finding, units, locator, limits, relevance, implication, stream, setup, eclass="numerical simulation",
      stype="derived simulation", comp="Rev H tracker (as built) on the same runs") -> Dict[str, str]:
    return L(id_, topic, "This ledger's calculation: ai2 (study L, AI and control v2), " + setup, "2026", "results/ai2/ai2.json",
             stype, eclass, "full text", setup, "none (simulation; synthetic writers)", comp, finding, units, locator, limits,
             relevance, "low", TRANSFER, implication, R2, "n/a (derived)", stream)


def derived(doc: Dict) -> List[Dict[str, str]]:
    agg = doc.get("aggregate") or {}
    sm, tf = agg.get("summary", {}), agg.get("tremor_free", {})
    pr = agg.get("paired", {})
    t = lambda v, k: _g(sm, v, k)  # noqa: E731
    rows = []
    tun = doc.get("tuning", {})
    d2b = _g(tun, "d2b", "selection", "chosen") or {}
    conf = _g(tun, "d2b", "confirmation_seed_301", "table") or {}
    conf_txt = "; ".join(f"{k.split('lam_max')[1].split('_')[0]} s nose {k[-1]}: R{''.join(str(int(v[r])) for r in ('R1', 'R2', 'R3', 'R4'))}"
                         for k, v in conf.items())
    kin = doc.get("lag_kinematics_calc") or {}

    def kr(lag, k, fmt="{:.2f}"):
        v = _g(kin, lag, k)
        return f"{_f(v[0], fmt)}-{_f(v[1], fmt)}" if v else "n/a"
    rows.append(D("CON-49", "Delayed ink: how far the hand moves during the lag and how much of the writing has a full lag inside the stroke (kinematics)",
                  f"Hand-ink distance over the lag (range over writers of the p95): 25 ms {kr('25ms', 'disp_p95_mm')} mm, 50 ms {kr('50ms', 'disp_p95_mm')} mm, "
                  f"100 ms {kr('100ms', 'disp_p95_mm')} mm, 250 ms {kr('250ms', 'disp_p95_mm')} mm; share of pen-down time with the full lag inside the same stroke: "
                  f"25 ms {kr('25ms', 'share_full_lag_in_stroke')}, 50 ms {kr('50ms', 'share_full_lag_in_stroke')}, 100 ms {kr('100ms', 'share_full_lag_in_stroke')}, "
                  f"250 ms {kr('250ms', 'share_full_lag_in_stroke')}",
                  "mm; share of pen-down time", "ai2.json lag_kinematics_calc; fig_lag_kinematics",
                  "Synthetic glyph writers (median pen-down speed about 12 mm/s), intended paths without tremor",
                  "Sets the nose travel a lagging ink needs and the lag beyond which stroke ends are lost",
                  "Lags above about 50 ms need more than +-3 mm of travel and lose stroke ends unless the contact itself is delayed", "CON",
                  "aiguide test writers 0-5, intended pen-down paths of 'return library books by friday'", eclass="calculation",
                  stype="derived calculation", comp="none"))
    rows.append(D("CON-50", "Delayed ink (fixed-lag RTS smoother, lag chosen per nose travel) vs the causal gated tracker and Rev H: test grid",
                  f"Ink error 1-2 mm: Rev H tracker {_f(t('tracker', 'ink_err_um_1_2mm'))} um, gated causal {_f(t('gated', 'ink_err_um_1_2mm'))} um, "
                  f"delayed +-3 mm {_f(t('delayed_3mm', 'ink_err_um_1_2mm'))} um, delayed +-6 mm {_f(t('delayed_6mm', 'ink_err_um_1_2mm'))} um, "
                  f"100 ms catch-up {_f(t('lag_100_6mm', 'ink_err_um_1_2mm'))} um; letters read 1-2 mm: tracker {_f(t('tracker', 'recognition_1_2mm'), '{:.3f}')}, "
                  f"gated {_f(t('gated', 'recognition_1_2mm'), '{:.3f}')}, delayed 3 mm {_f(t('delayed_3mm', 'recognition_1_2mm'), '{:.3f}')}, "
                  f"delayed 6 mm {_f(t('delayed_6mm', 'recognition_1_2mm'), '{:.3f}')}; paired delayed 3 mm - gated ink "
                  f"{_f(_g(pr, 'delayed_3mm-gated:ink_err_um', 'mean'), '{:+.0f}')} um (95 % CI {_f((_g(pr, 'delayed_3mm-gated:ink_err_um', 'ci95') or [None])[0], '{:+.0f}')} to "
                  f"{_f((_g(pr, 'delayed_3mm-gated:ink_err_um', 'ci95') or [None, None])[1], '{:+.0f}')}). Chosen on tuning seed 300: "
                  + "; ".join(f"{k}: lag <= {1e3 * float(v.split('lam_max')[1].split('_')[0]):.0f} ms" for k, v in d2b.items() if v)
                  + f"; seed-301 confirmation (R1R2R3R4): {conf_txt}; not adopted (R3 failed on seed 301)",
                  "um RMS ink error; share of letters read", "ai2.json aggregate.summary, aggregate.paired, tuning.d2b",
                  "Model HW1 replay convention; a +-6 mm nose is an assumption (same servo)", "Whether a small ink lag buys a cleaner line",
                  "Adopt the causal gated tracker; keep delayed ink as an option only if EXP-L01/L02 show writers accept the lag", "CON",
                  "aiguide test writers 0-5 x seeds 200-203 x 6/8/10 Hz x 0.3/1/2 mm (216 scenarios)"))
    rows.append(D("CON-51", "Delayed ink: stroke ends, contact delay (Z-actuated refill) and nose travel needed",
                  f"Coverage of the intended path within 0.3 mm, 1-2 mm tremor: gated {_f(t('gated', 'coverage_1_2mm'), '{:.3f}')}, 100 ms catch-up "
                  f"{_f(t('lag_100_6mm', 'coverage_1_2mm'), '{:.3f}')}, 100 ms with delayed contact {_f(t('limit_100_6mm', 'coverage_1_2mm'), '{:.3f}')}; letters read "
                  f"{_f(t('lag_100_6mm', 'recognition_1_2mm'), '{:.3f}')} vs {_f(t('limit_100_6mm', 'recognition_1_2mm'), '{:.3f}')}; nose travel needed p95: gated "
                  f"{_f(t('gated', 'q_p95_mm_1_2mm'), '{:.2f}')} mm, 50 ms {_f(t('lag_50_6mm', 'q_p95_mm_1_2mm'), '{:.2f}')} mm, 100 ms {_f(t('lag_100_6mm', 'q_p95_mm_1_2mm'), '{:.2f}')} mm",
                  "share; mm", "ai2.json aggregate.summary", "The delayed-contact case is an upper bound (the refill's Z motion is not modelled)",
                  "A lag needs both travel and a way to finish strokes", "Do not pursue lags above 50 ms without a Z-actuated refill", "CON",
                  "aiguide test writers 0-5 x seeds 200-203 x 6/8/10 Hz x 1-2 mm"))
    A = _g(doc, "synth", "A_synthetic_writers") or {}
    B = _g(doc, "synth", "B_character_trajectories") or {}
    Cc = _g(doc, "synth", "C_uji_generator") or {}
    rows.append(D("CON-52", "Handwriting synthesis in the writer's style: sigma-lognormal from 1-3 samples; learned few-shot generator on UJI",
                  f"Synthetic writers 0-5: legible (app recogniser) font {_f(_g(A, 'font', 'legibility'), '{:.2f}')}, copy {_f(_g(A, 'copy', 'legibility'), '{:.2f}')}, "
                  f"sigma-lognormal k=1 {_f(_g(A, 'sl_k1', 'legibility'), '{:.2f}')}, k=3 {_f(_g(A, 'sl_k3', 'legibility'), '{:.2f}')}; writer identified (chance "
                  f"{_f(_g(A, 'chance_writer_id'), '{:.2f}')}): font {_f(_g(A, 'font', 'writer_id_acc'), '{:.2f}')}, sigma-lognormal k=3 {_f(_g(A, 'sl_k3', 'writer_id_acc'), '{:.2f}')}; "
                  f"extraction SNR median {_f(_g(A, 'extraction_snr_db', 'median'), '{:.1f}')} dB (synthetic), {_f(_g(B, 'snr_db_median'), '{:.1f}')} dB (real velocity, one writer); "
                  f"UJI few-shot generator: legible {_f(_g(Cc, 'generated_legibility'), '{:.2f}')} (real test letters {_f(_g(Cc, 'classifier_acc_real_test_letters'), '{:.2f}')}), "
                  f"same-writer preference {_f(_g(Cc, 'same_writer_preference_generated'), '{:.2f}')} vs class mean {_f(_g(Cc, 'same_writer_preference_class_mean'), '{:.2f}')} (chance 0.5)",
                  "share; dB", "ai2.json synth", "Synthetic writers are glyph-font based; UJI has shapes only",
                  "Whether autowrite and templates can look like the user's own writing from a 20 s sample", "Use sigma-lognormal synthesis from the calibration letters; measure style on real writers (EXP-L05)", "CON",
                  "aiguide writers 0-5 (26 letters, 3 held-out instances); UCI Character Trajectories; UCI UJI Pen Characters v2", eclass="calculation",
                  stype="derived calculation", comp="font in the writer's style; copy of one reference instance"))
    det = agg.get("gate_open_frac_by_condition", {})
    rows.append(D("PDT-45", "Tremor-line detector gate: open fraction by condition and on tremor-free writing (test writers)",
                  f"Gate open fraction (mean over writers and seeds): tremor-free {_f(agg.get('gate_open_frac_tremor_free'), '{:.3f}')}; 6 Hz 0.3/1/2 mm "
                  f"{_f(det.get('6Hz_0.3mm'), '{:.2f}')}/{_f(det.get('6Hz_1mm'), '{:.2f}')}/{_f(det.get('6Hz_2mm'), '{:.2f}')}; 8 Hz {_f(det.get('8Hz_0.3mm'), '{:.2f}')}/"
                  f"{_f(det.get('8Hz_1mm'), '{:.2f}')}/{_f(det.get('8Hz_2mm'), '{:.2f}')}; 10 Hz {_f(det.get('10Hz_0.3mm'), '{:.2f}')}/{_f(det.get('10Hz_1mm'), '{:.2f}')}/"
                  f"{_f(det.get('10Hz_2mm'), '{:.2f}')} (includes the 4.5 s start-up of each 20 s recording)",
                  "share of time", "ai2.json aggregate.gate_open_frac_*", "Synthetic tremor with fixed frequency per recording",
                  "The gate is what keeps tremor-free writing untouched", "Keep the detector state across lines in a session so the start-up is paid once", "PDT",
                  "aiguide test writers 0-5 x seeds 200-203; detector r_on 5, r_off 2.5, 4 s window", comp="none"))
    rows.append(D("PDT-46", "Causal gated listening tracker (model-based stack) vs the Rev H tracker, by tremor frequency",
                  f"Ink error 1-2 mm at 6/8/10 Hz: tracker {_f(t('tracker', 'ink_err_um_6Hz_1_2mm'))}/{_f(t('tracker', 'ink_err_um_8Hz_1_2mm'))}/{_f(t('tracker', 'ink_err_um_10Hz_1_2mm'))} um, "
                  f"gated {_f(t('gated', 'ink_err_um_6Hz_1_2mm'))}/{_f(t('gated', 'ink_err_um_8Hz_1_2mm'))}/{_f(t('gated', 'ink_err_um_10Hz_1_2mm'))} um; "
                  f"0.3 mm: tracker {_f(t('tracker', 'ink_err_um_0p3mm'))} um, gated {_f(t('gated', 'ink_err_um_0p3mm'))} um; tremor-free moved: tracker "
                  f"{_f(_g(tf, 'tracker', 'false_correction_um'), '{:.1f}')} um, gated {_f(_g(tf, 'gated', 'false_correction_um'), '{:.1f}')} um; paired gated - tracker ink 1-2 mm "
                  f"{_f(_g(pr, 'gated-tracker:ink_err_um', 'mean'), '{:+.0f}')} um (95 % CI {_f((_g(pr, 'gated-tracker:ink_err_um', 'ci95') or [None])[0], '{:+.0f}')} to "
                  f"{_f((_g(pr, 'gated-tracker:ink_err_um', 'ci95') or [None, None])[1], '{:+.0f}')})",
                  "um RMS", "ai2.json aggregate.summary, aggregate.tremor_free, aggregate.paired", "Model HW1; synthetic tremor",
                  "The biggest gain found here comes from listening harder only when a tremor line is present", "Adopt as the Rev J firmware estimator (proposed DEC)", "PDT",
                  "aiguide test writers 0-5 x seeds 200-203 x 6/8/10 Hz x 0.3/1/2 mm"))
    lm = doc.get("learn") or {}
    lmods = lm.get("models", {})
    rows.append(D("EML-66", "Learned tremor estimators (TCN, calibrated TCN, hybrid Kalman-network, transformer) trained with domain randomisation",
                  "Open loop on tuning writers (J = residual 1-2 mm + false-correction guard, um): " +
                  ", ".join(f"{m} {_f(v.get('J'))} ({v.get('n_params')} parameters, {v.get('macs_per_step')} MAC/step)" for m, v in lmods.items()) +
                  f"; model-based stack {_f(_g(lm, 'reference', 'model_based_stack', 'J'))}; Rev H {_f(_g(lm, 'reference', 'revh_tracker', 'J'))}. Test grid ink 1-2 mm: " +
                  ", ".join(f"{k} {_f(t(k, 'ink_err_um_1_2mm'))} um (tremor-free {_f(_g(tf, k, 'false_correction_um'), '{:.1f}')} um)" for k in
                            ("learned_tcn", "learned_ctx", "learned_hybrid", "learned_transformer") if k in sm),
                  "um RMS", "ai2.json learn, aggregate.summary, tuning.cl", "Synthetic training and test data only; no real tremor recordings",
                  "Whether ML beats the model-based stack in this simulator", "Keep the model-based stack; a learned estimator must pass REQ-ML-001 on real recordings first", "EML",
                  f"320 domain-randomised synthetic writers (writers 1000+), CPU training {_f(sum((v.get('train_minutes') or 0) for v in lmods.values()), '{:.0f}')} min in total"))
    rl = doc.get("rl") or {}
    pol = rl.get("policies", {})
    rows.append(D("EML-67", "RL for shared control of the nose: PPO/SAC arbiter and residual PPO (Gymnasium, HW1 replay backend)",
                  "Tuning replay reward (vs Rev H for the arbiter, vs the model-based stack for the residual): " +
                  ", ".join(f"{k} {_f(_g(v, 'best', 'reward_mean'), '{:.2f}')} after {v.get('env_steps')} steps ({_f(v.get('wall_min'), '{:.0f}')} min)" for k, v in pol.items()) +
                  f"; model-based gate {_f(_g(rl, 'model_based_arbiter', 'reward_mean'), '{:.2f}')}. Test grid ink 1-2 mm: RL arbiter {_f(t('rl_arbiter', 'ink_err_um_1_2mm'))} um, residual RL "
                  f"{_f(t('rl_residual', 'ink_err_um_1_2mm'))} um, gated {_f(t('gated', 'ink_err_um_1_2mm'))} um; tremor-free moved: arbiter {_f(_g(tf, 'rl_arbiter', 'false_correction_um'), '{:.1f}')} um, "
                  f"residual {_f(_g(tf, 'rl_residual', 'false_correction_um'), '{:.1f}')} um",
                  "reward per decision; um RMS", "ai2.json rl, aggregate.summary", "Replay backend (no closed-loop training); synthetic writers",
                  "What RL adds on top of the model-based stack", "Use RL for arbitration only after sim2 closed-loop training and EXP-L03", "EML",
                  "Stable-Baselines3 2.9, one CPU thread; 320 randomised training episodes; tuning writers 100-103", comp="model-based gate and the Rev H tracker"))
    tx = doc.get("text") or {}
    ev = tx.get("eval", {})
    g = lambda m, s, k, sub: _g(ev, m, s, k, sub)  # noqa: E731
    rows.append(D("EML-68", "Next-letter (two ahead) and next-word prediction: n-gram vs small character transformer on CC0 text",
                  "Tatoeba test, letter two ahead top-1/top-3: " + ", ".join(f"{m} {_f(g(m, 'tatoeba_test', 'glyph_d2', 'top1'), '{:.3f}')}/{_f(g(m, 'tatoeba_test', 'glyph_d2', 'top3'), '{:.3f}')}"
                                                                          for m in ("NG0", "NG1", "TF_small", "TF", "MIX") if m in ev) +
                  "; next word top-1/top-3: " + ", ".join(f"{m} {_f(g(m, 'tatoeba_test', 'next_word', 'top1'), '{:.3f}')}/{_f(g(m, 'tatoeba_test', 'next_word', 'top3'), '{:.3f}')}"
                                                          for m in ("NG0", "NG1", "TF_small", "TF", "MIX") if m in ev) +
                  f"; transformer {_f(_g(tx, 'models', 'TF', 'n_params'))} parameters ({_f(_g(tx, 'models', 'TF', 'mcu_ms_per_char_int8'), '{:.1f}')} ms per character on a 128 MHz MCU, int8, CALC); "
                  f"small {_f(_g(tx, 'models', 'TF_small', 'n_params'))} parameters ({_f(_g(tx, 'models', 'TF_small', 'mcu_ms_per_char_int8'), '{:.2f}')} ms)",
                  "top-k accuracy; ms; parameters", "ai2.json text", "Sentence corpora, not notes; CPU latency on this container",
                  "How much better prediction the pen and app can have", "Ship the mixture on the phone; the small model or n-gram on the pen", "EML",
                  "Tatoeba CC0 + Common Voice CC0 sentence text; test splits used once", eclass="calculation", stype="derived calculation",
                  comp="aiguide n-gram predictor (NG0) as used so far"))
    sh = doc.get("shared") or {}
    st_ = sh.get("test", {})
    rows.append(D("EML-69", "Shared control for guided practice: fixed guidance vs assistance-as-needed (per-letter gain with forgetting factor)",
                  "Test learners (dysgraphia-like, passive hand): " + ", ".join(
                      f"{k} target {_f(_g(st_, k, 'target_err_um'))} um, device share {_f(_g(st_, k, 'device_share'), '{:.2f}')}, gain on malformed/well-formed letters "
                      f"{_f(_g(st_, k, 'gain_on_malformed'), '{:.2f}')}/{_f(_g(st_, k, 'gain_on_wellformed'), '{:.2f}')}" for k in ("fixed_partial", "fixed_full", "aan", "aan_fade") if k in st_) +
                  f"; chosen AAN setting (tuning learners, rule S1): {sh.get('chosen')}",
                  "um RMS; share", "ai2.json shared", "The simulated learner does not learn, so no learning benefit can be shown",
                  "How the pen decides how much to help and hands control back", "Use AAN with a forgetting factor for guidance; test learning in EXP-L04", "EML",
                  "handwriting study's dysgraphia-like learners, test writers 0-5 x seeds 200-203", comp="fixed partial guidance (gain 0.5)"))
    cl = _g(tun, "cl") or {}
    cad = cl.get("adopted")
    rows.append(D("PDT-47", "Per-user calibration (20 s) of the learned estimator and closed-loop tuning check of learned and RL candidates",
                  f"Closed-loop tuning check (seeds 300-301, rules R1-R4 vs Rev H): passing {cl.get('passing')}; adopted {cad}; " +
                  ", ".join(f"{k} J {_f(v.get('J_ink_1_2mm_um'))} um fc {_f(v.get('fc_um'), '{:.1f}')} um" for k, v in (cl.get('table') or {}).items()),
                  "um RMS", "ai2.json tuning.cl", "Calibration = the detector on a separate synthetic recording",
                  "Whether per-user calibration helps a learned estimator", "Calibrate the detector band and the context input from the 20 s calibration; confirm on real users (EXP-L03)", "PDT",
                  "aiguide tuning writers 100-103, seeds 300-301"))
    return rows


def write_rows(path: Path, doc: Dict) -> None:
    hdr = header()
    rows = literature() + derived(doc)
    rows.sort(key=lambda r: (r["stream"], int(r["id"].split("-")[1])))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=hdr)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in hdr})
