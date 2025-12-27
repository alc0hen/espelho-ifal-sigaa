import json

def get_demo_data():
    """
    Generator that yields demo data messages similar to the real SIGAA stream.
    """

    # 1. User Info
    yield {
        "type": "user_info",
        "name": "Aluno Demonstração",
        "is_supporter": True
    }

    # Course 1: High Grades (Approved) - "Nerd Supremo" achievement candidate
    c1_id = 1
    yield {
        "type": "course_start",
        "id": c1_id,
        "name": "Matemática Aplicada",
        "obs": "Técnico em Informática"
    }
    yield {
        "type": "course_data",
        "id": c1_id,
        "data": {
            'b1Notes': [10.0],
            'b2Notes': [9.5, 10.0],
            'b3Notes': [10.0],
            'b4Notes': [9.0],
            'r1Note': None,
            'r2Note': None
        }
    }
    yield {
        "type": "course_frequency",
        "id": c1_id,
        "data": {
            "total_faltas": 2,
            "max_faltas": 20,
            "percent": 2.5
        }
    }

    # Course 2: Struggling but surviving (Recovery)
    c2_id = 2
    yield {
        "type": "course_start",
        "id": c2_id,
        "name": "Física I",
        "obs": "Técnico em Informática"
    }
    yield {
        "type": "course_data",
        "id": c2_id,
        "data": {
            'b1Notes': [4.0, 3.5],
            'b2Notes': [5.0],
            'b3Notes': [6.0, 5.5],
            'b4Notes': [4.0],
            'r1Note': 7.5, # Recovery S1
            'r2Note': None
        }
    }
    yield {
        "type": "course_frequency",
        "id": c2_id,
        "data": {
            "total_faltas": 12,
            "max_faltas": 20,
            "percent": 15.0
        }
    }

    # Course 3: Critical Failure (Frequency)
    c3_id = 3
    yield {
        "type": "course_start",
        "id": c3_id,
        "name": "Programação Web",
        "obs": "Técnico em Informática"
    }
    yield {
        "type": "course_data",
        "id": c3_id,
        "data": {
            'b1Notes': [8.0],
            'b2Notes': [7.5],
            'b3Notes': [8.0],
            'b4Notes': [9.0],
            'r1Note': None,
            'r2Note': None
        }
    }
    yield {
        "type": "course_frequency",
        "id": c3_id,
        "data": {
            "total_faltas": 25,
            "max_faltas": 20,
            "percent": 31.2
        }
    }

    # Course 4: In Progress (Waiting for B4)
    c4_id = 4
    yield {
        "type": "course_start",
        "id": c4_id,
        "name": "Língua Portuguesa",
        "obs": "Técnico em Informática"
    }
    yield {
        "type": "course_data",
        "id": c4_id,
        "data": {
            'b1Notes': [7.0],
            'b2Notes': [6.5],
            'b3Notes': [8.0],
            'b4Notes': [], # Missing
            'r1Note': None,
            'r2Note': None
        }
    }
    yield {
        "type": "course_frequency",
        "id": c4_id,
        "data": {
            "total_faltas": 8,
            "max_faltas": 20,
            "percent": 10.0
        }
    }
