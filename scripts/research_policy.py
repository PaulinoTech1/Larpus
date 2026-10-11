"""Owner-reviewed source policy for the research archive. Used by curation and index builds only."""
import re
import urllib.parse

# Each host is a university repository, standards body, peer-reviewed publisher or
# the primary authors' own algorithm site. Adding a host is a deliberate review step.
RESEARCH_HOSTS = {
    'dspace.mit.edu',             # MIT institutional repository
    'thesis.caltech.edu',         # CaltechTHESIS files
    'thesis.library.caltech.edu', # CaltechTHESIS records
    'repositori-api.upf.edu',     # Universitat Pompeu Fabra repository
    'www.cs.ru.nl',               # Radboud University computing science theses
    'csrc.nist.gov',              # NIST Computer Security Resource Center
    'nvlpubs.nist.gov',           # NIST publications
    'pq-crystals.org',            # CRYSTALS (Kyber/Dilithium) authors' reference site
    'msp.org',                    # Mathematical Sciences Publishers (Pacific J. Math.)
    # Mathematician expansion (2026-10-10). DOI/handle resolvers are deliberately not
    # listed: those landing URLs were replaced by the institutional repository records.
    'www.repository.cam.ac.uk',   # University of Cambridge Apollo repository records
    'api.repository.cam.ac.uk',   # University of Cambridge Apollo repository files
    'spiral.imperial.ac.uk',      # Imperial College London Spiral repository
    'repository.gatech.edu',      # Georgia Institute of Technology SMARTech repository
    'textbooks.math.gatech.edu',  # Georgia Institute of Technology mathematics textbooks
    'www2.isye.gatech.edu',       # Georgia Institute of Technology ISyE faculty pages
    'dspace.library.uu.nl',       # Utrecht University repository
    'www.research-collection.ethz.ch', # ETH Zurich Research Collection
    'ocw.mit.edu',                # MIT OpenCourseWare
    'math.mit.edu',               # MIT Department of Mathematics faculty pages
    'people.math.harvard.edu',    # Harvard University Department of Mathematics
    'people.math.wisc.edu',       # University of Wisconsin-Madison Mathematics
    'pi.math.cornell.edu',        # Cornell University Department of Mathematics
    'web.math.princeton.edu',     # Princeton University Department of Mathematics
    'web.stanford.edu',           # Stanford University faculty pages
    'mathweb.ucsd.edu',           # UC San Diego Department of Mathematics
    'www.math.ucdavis.edu',       # UC Davis Department of Mathematics
    'www.math.uchicago.edu',      # University of Chicago Department of Mathematics
    'www.math.brown.edu',         # Brown University Department of Mathematics
    'www.math.colostate.edu',     # Colorado State University Department of Mathematics
    'www.mat.univie.ac.at',       # University of Vienna Faculty of Mathematics
    'www.whitman.edu',            # Whitman College Department of Mathematics
    # Linux kernel / virtualization security expansion (2026-10-10): official project
    # documentation, government advisories and university thesis repositories.
    'docs.kernel.org',            # Linux kernel project documentation
    'kspp.github.io',             # Kernel Self Protection Project (kernel.org security initiative)
    'www.qemu.org',               # QEMU project official site and documentation
    'xenproject.org',             # Xen Project (Linux Foundation) official site
    'xenbits.xen.org',            # Xen Project security advisories (XSA)
    'www.qubes-os.org',           # Qubes OS project official site
    'doc.qubes-os.org',           # Qubes OS official documentation
    'ubuntu.com',                 # Canonical Ubuntu security CVE tracker
    'documentation.ubuntu.com',   # Canonical Ubuntu official documentation
    'wiki.archlinux.org',         # Arch Linux official wiki
    'www.kali.org',               # Kali Linux (OffSec) official documentation
    'linuxmint-installation-guide.readthedocs.io', # Linux Mint official installation guide
    'www.cisa.gov',               # US Cybersecurity and Infrastructure Security Agency
    'www.ndss-symposium.org',     # NDSS Symposium (Internet Society) peer-reviewed proceedings
    'www.cl.cam.ac.uk',           # University of Cambridge Computer Laboratory technical reports
    'www.cs.columbia.edu',        # Columbia University Computer Science (thesis PDF)
    'academiccommons.columbia.edu', # Columbia University Academic Commons repository
    'utoronto.scholaris.ca',      # University of Toronto TSpace/Scholaris repository
    'vtechworks.lib.vt.edu',      # Virginia Tech VTechWorks repository
    'air.unimi.it',               # University of Milan AIR repository
    # Second linux-kernel-expert batch (2026-10-10).
    'cdrdv2-public.intel.com',    # Intel Corporation public technical documents (VT-d specification)
    'www.intel.com',              # Intel Corporation document landing pages
    'docs.amd.com',               # AMD official technical documentation (IOMMU specification)
    'csilinux.com',               # CSI Linux project official documentation
    'security.archlinux.org',     # Arch Linux Security Team advisory tracker
    'lirias.kuleuven.be',         # KU Leuven Lirias institutional repository
    'www.its.uni-luebeck.de',     # University of Luebeck Institute for IT Security
    'diglib.tugraz.at',           # Graz University of Technology digital library
    'www.cs.umd.edu',             # University of Maryland Computer Science (dissertation PDF)
    'drum.lib.umd.edu',           # University of Maryland DRUM repository (degree record)
    # Peer-reviewed postdoctoral papers (2026-10-10).
    'tosc.iacr.org',              # IACR Transactions on Symmetric Cryptology (open access)
    'tches.iacr.org',             # IACR Transactions on Cryptographic Hardware and Embedded Systems
    'quantum-journal.org',        # Quantum, the open journal for quantum science (peer-reviewed)
    'www.cambridge.org',          # Cambridge University Press (Cambridge Core journals)
    'www.usenix.org',             # USENIX Association open-access proceedings
    # Early-career peer-reviewed papers (2026-10-10).
    'projecteuclid.org',          # Project Euclid (IMS/Bernoulli peer-reviewed statistics journals)
    'repository.tudelft.nl',      # Delft University of Technology repository
    'journals.uwyo.edu',          # University of Wyoming: Electronic Journal of Linear Algebra (ILAS)
    'ir.cwi.nl',                  # CWI Amsterdam institutional repository
    'purehost.bath.ac.uk',        # University of Bath Pure research repository
    # Owner-approved exception 2026-10-10: Linux Mint's official blog, used only for the
    # project's own 2016 ISO compromise incident statement.
    'blog.linuxmint.com',
}
LEVELS = {'undergraduate', 'masters', 'phd', 'references'}
# Optional per-entry rights tag for training-data export: 'allowed' or 'private-only'.
# Absent means not cleared; only 'allowed' entries may enter shareable fine-tuning data.
TRAINING_USE = {'allowed', 'private-only'}
# Stored original format. HTML is official documentation kept byte-exact and SHA-256
# pinned like PDFs; it is indexed through the same HTML text extractor as web sources.
FORMATS = {'pdf', 'html', 'txt'}

# Hosts that are never trusted as a whole: only exact path prefixes are reviewed.
# raw.githubusercontent.com serves any GitHub user's files, so only the PGP-signed
# Qubes OS security pack (official Qubes Security Bulletins) is accepted (2026-10-10).
RESEARCH_PATH_PREFIXES = {
    'raw.githubusercontent.com': ('/QubesOS/qubes-secpack/',),
}


def vetted_host(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError('Research URL must be plain HTTPS without credentials or custom ports')
    if parsed.hostname in RESEARCH_PATH_PREFIXES:
        path = parsed.path
        if (parsed.query or parsed.fragment or '..' in path or '%' in path or '\\' in path
                or not any(path.startswith(p) for p in RESEARCH_PATH_PREFIXES[parsed.hostname])):
            raise ValueError(f'Research path is not on the reviewed prefix list: {parsed.hostname}{path}')
        return parsed.hostname
    if parsed.hostname not in RESEARCH_HOSTS:
        raise ValueError(f'Research host is not on the reviewed list: {parsed.hostname}')
    return parsed.hostname


def vet(entry):
    """Refuse any catalog entry that is not traceable to a reviewed publisher with pinned bytes."""
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,120}', entry.get('id', '')):
        raise ValueError('Invalid research identity')
    if entry.get('level') not in LEVELS:
        raise ValueError(f'{entry["id"]}: invalid level')
    for key in ('source_url', 'download_url', 'degree_evidence_url'):
        vetted_host(entry[key])
    if not entry.get('title') or not entry.get('authors') or not entry.get('year'):
        raise ValueError(f'{entry["id"]}: title, authors and year are required')
    if not entry.get('rights'):
        raise ValueError(f'{entry["id"]}: rights statement is required')
    if entry.get('format', 'pdf') not in FORMATS:
        raise ValueError(f'{entry["id"]}: invalid format')
    if 'training_use' in entry and entry['training_use'] not in TRAINING_USE:
        raise ValueError(f'{entry["id"]}: invalid training_use')
    if entry.get('level') != 'references' and not entry.get('degrees'):
        raise ValueError(f'{entry["id"]}: degree evidence is required for student works')
    if entry.get('full_text_status') == 'downloaded':
        if not re.fullmatch(r'[a-f0-9]{64}', entry.get('sha256') or ''):
            raise ValueError(f'{entry["id"]}: downloaded text must be SHA-256 pinned')
        if not isinstance(entry.get('bytes'), int) or entry['bytes'] <= 0:
            raise ValueError(f'{entry["id"]}: pinned byte size is required')
    return entry