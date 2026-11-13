"""A curated list of IT skills, so suggestions are things a CV can actually claim.

shortcut: a hand-kept list; skills missing from it are never suggested. Add entries here as
new tools show up in job ads.
"""

import re

SKILLS = (
    # languages
    "python java javascript typescript c# c++ php ruby kotlin swift scala rust golang perl "
    "bash powershell sql plsql t-sql html css sass dart objective-c matlab cobol vba "
    # web and mobile
    "react angular vue svelte next.js nuxt node.js express django flask fastapi spring "
    "asp.net .net laravel rails jquery graphql rest soap grpc webpack vite tailwind "
    "bootstrap react-native flutter android ios xamarin electron wordpress drupal magento "
    "shopify sitecore salesforce "
    # cloud and devops
    "aws azure gcp kubernetes docker terraform ansible puppet jenkins gitlab github "
    "bitbucket git ci/cd helm argocd cloudformation bicep pulumi prometheus grafana "
    "datadog splunk elk new-relic nginx apache serverless lambda microservices openshift "
    "vmware hyper-v proxmox cloudflare "
    # data and ai
    "postgresql mysql sqlite oracle mongodb dynamodb redis cassandra elasticsearch "
    "opensearch snowflake bigquery redshift databricks spark pyspark hadoop kafka airflow "
    "dbt etl elt power-bi tableau looker qlik excel pandas numpy scikit-learn tensorflow "
    "pytorch keras nlp llm machine-learning deep-learning data-science data-engineering "
    "data-warehouse data-modelling data-governance mlops sas "
    # security and networking
    "cybersecurity siem soc penetration-testing owasp iso-27001 nist soc-2 firewall vpn "
    "okta sso oauth iam pki encryption vulnerability-management crowdstrike sentinel "
    "tcp/ip dns dhcp bgp ospf cisco juniper fortinet palo-alto meraki wi-fi sd-wan lan wan "
    "load-balancing "
    # systems and infrastructure
    "linux windows-server active-directory exchange sharepoint intune sccm office-365 "
    "microsoft-365 azure-ad entra vmware-esxi citrix storage backup disaster-recovery "
    "virtualisation unix macos "
    # service, process and business tools
    "itil servicenow jira confluence zendesk service-desk help-desk remedy sap dynamics "
    "netsuite xero myob workday oracle-ebs power-automate power-apps powerapps sharepoint "
    "agile scrum kanban devops devsecops sre tdd bdd safe prince2 pmp lean six-sigma "
    "business-analysis requirements-gathering user-stories uat stakeholder-management "
    "change-management vendor-management "
    # testing and quality
    "selenium cypress playwright jest junit pytest postman soapui jmeter load-testing "
    "test-automation manual-testing qa unit-testing "
    # design and misc
    "figma sketch photoshop ux ui user-research api-design "
    # certifications
    "ccna ccnp comptia-a+ comptia-security+ comptia-network+ cissp cism cisa ceh "
    "az-900 az-104 az-204 az-305 aws-certified "
)

# Other ways ads write the same skill.
ALIASES = {
    "javascript": ("js", "ecmascript", "es6"),
    "typescript": ("ts",),
    "kubernetes": ("k8s",),
    "postgresql": ("postgres",),
    "node.js": ("nodejs", "node js"),
    "next.js": ("nextjs",),
    "vue": ("vue.js", "vuejs"),
    "react": ("react.js", "reactjs"),
    "angular": ("angularjs",),
    "golang": ("go lang",),
    "asp.net": ("asp net",),
    ".net": ("dotnet", ".net core", "dot net"),
    "aws": ("amazon web services",),
    "gcp": ("google cloud", "google cloud platform"),
    "azure": ("microsoft azure",),
    "ci/cd": ("cicd", "ci cd"),
    "power-bi": ("power bi", "powerbi"),
    "machine-learning": ("machine learning", "ml"),
    "deep-learning": ("deep learning",),
    "data-science": ("data science",),
    "data-engineering": ("data engineering",),
    "data-warehouse": ("data warehouse", "data warehousing"),
    "data-modelling": ("data modelling", "data modeling"),
    "data-governance": ("data governance",),
    "scikit-learn": ("sklearn", "scikit learn"),
    "mongodb": ("mongo",),
    "elasticsearch": ("elastic search",),
    "elk": ("elastic stack",),
    "new-relic": ("new relic", "newrelic"),
    "penetration-testing": ("penetration testing", "pen testing", "pentesting"),
    "iso-27001": ("iso 27001", "iso27001"),
    "soc-2": ("soc 2", "soc2"),
    "palo-alto": ("palo alto",),
    "wi-fi": ("wifi", "wi fi"),
    "sd-wan": ("sd wan", "sdwan"),
    "load-balancing": ("load balancing", "load balancer"),
    "windows-server": ("windows server",),
    "active-directory": ("active directory",),
    "office-365": ("office 365", "o365"),
    "microsoft-365": ("microsoft 365", "m365"),
    "azure-ad": ("azure ad", "azure active directory"),
    "vmware-esxi": ("esxi",),
    "disaster-recovery": ("disaster recovery",),
    "virtualisation": ("virtualization", "virtualisation"),
    "service-desk": ("service desk",),
    "help-desk": ("help desk", "helpdesk"),
    "oracle-ebs": ("oracle ebs",),
    "power-automate": ("power automate",),
    "power-apps": ("power apps", "powerapps"),
    "six-sigma": ("six sigma",),
    "business-analysis": ("business analysis", "business analyst"),
    "requirements-gathering": ("requirements gathering",),
    "user-stories": ("user stories",),
    "stakeholder-management": ("stakeholder management",),
    "change-management": ("change management",),
    "vendor-management": ("vendor management",),
    "load-testing": ("load testing", "performance testing"),
    "test-automation": ("test automation", "automated testing"),
    "manual-testing": ("manual testing",),
    "unit-testing": ("unit testing",),
    "user-research": ("user research",),
    "api-design": ("api design",),
    "react-native": ("react native",),
    "comptia-a+": ("comptia a+", "a+ certification"),
    "comptia-security+": ("security+", "comptia security+"),
    "comptia-network+": ("network+", "comptia network+"),
    "aws-certified": ("aws certified",),
    "github": ("github actions",),
    "gitlab": ("gitlab ci",),
    "ux": ("user experience",),
    "ui": ("user interface",),
    "salesforce": ("sfdc",),
    "sharepoint": ("share point",),
    "microservices": ("micro services", "microservice"),
    "devops": ("dev ops",),
}


def _display(key: str) -> str:
    """Hyphenated keys read as phrases in ads ("power-bi" -> "power bi"), except real names."""
    return (
        key
        if key in {"ci/cd", "wi-fi", "t-sql", "objective-c", "react-native"}
        else key.replace("-", " ")
    )


_ALIAS_TO_SKILL: dict[str, str] = {}
for _skill in SKILLS.split():
    _ALIAS_TO_SKILL[_skill] = _skill
    _ALIAS_TO_SKILL[_display(_skill)] = _skill
for _skill, _names in ALIASES.items():
    for _name in _names:
        _ALIAS_TO_SKILL[_name] = _skill

SKILL_KEYS = frozenset(_ALIAS_TO_SKILL.values())

# Longest first so "react native" wins over "react"; the guards stop "java" matching inside
# "javascript" or "sql" inside "mysql" while still allowing "c++" and "node.js".
_PATTERN = re.compile(
    r"(?<![a-z0-9+#.])("
    + "|".join(re.escape(name) for name in sorted(_ALIAS_TO_SKILL, key=len, reverse=True))
    + r")(?![a-z0-9+#])"
)


def find_skills(text: str) -> set[str]:
    """Skills named in `text`, each as its canonical key (aliases collapse into one)."""
    return {_ALIAS_TO_SKILL[match] for match in _PATTERN.findall(text.lower())}
