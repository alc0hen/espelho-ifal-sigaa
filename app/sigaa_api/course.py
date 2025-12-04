from .exceptions import SigaaConnectionError


class Course:
    def __init__(self, session, title, form_data):
        self.session = session
        self.title = title
        self.form_data = form_data
        self.id = form_data['post_values'].get('idTurma')
        self.grades = []

    def __repr__(self):
        return f"<Course title='{self.title}'>"

    async def get_grades(self):

        course_page = await self._enter_course()

        # 2. Navigate to "Ver Notas"
        grades_page = await self._navigate_to_grades(course_page)

        # 3. Parse grades
        self.grades = self._parse_grades(grades_page)
        return self.grades

    async def _enter_course(self):
        page = await self.session.post(
            self.form_data['action'],
            data=self.form_data['post_values']
        )
        return page

    async def _navigate_to_grades(self, course_page):
        menu_items = course_page.soup.find_all(string="Ver Notas")
        for item in menu_items:
            parent = item.parent
            while parent:
                if parent.name in ['td', 'div', 'a']:
                    if parent.get('onclick'):
                        js_code = parent['onclick']
                        form_data = course_page.parse_jsfcljs(js_code)
                        page = await self.session.post(
                            form_data['action'],
                            data=form_data['post_values']
                        )
                        return page
                parent = parent.parent
                if not parent or parent.name == 'body':
                    break

        raise ValueError("Could not find 'Ver Notas' menu item.")

    def _parse_grades(self, page):
        grades = []

        table = page.soup.find('table', class_='tabelaRelatorio')
        if not table:
            return []

        thead = table.find('thead')
        tbody = table.find('tbody')

        if not thead or not tbody:
            return []

        # Get header rows
        header_rows = thead.find_all('tr')
        if not header_rows:
            return []

        # First row has the main headers (Unidade 1, 2, 3, etc)
        main_headers = header_rows[0].find_all('th')

        # Second row (if exists) has sub-headers (A1, A2, Nota, etc)
        sub_headers_row = header_rows[1] if len(header_rows) > 1 else None

        # Build a clean list of sub-headers (only non-empty ones with their positions)
        sub_headers_clean = []
        if sub_headers_row:
            all_sub_headers = sub_headers_row.find_all('th')
            for idx, sh in enumerate(all_sub_headers):
                text = sh.get_text(strip=True)
                if text:  # Only non-empty headers
                    sub_headers_clean.append({
                        'index': idx,
                        'text': text,
                        'id': sh.get('id', '')
                    })

        # Find the STUDENT'S data row in tbody
        # Look for a row with the student's name or matricula
        student_row = None
        for row in tbody.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) > 1:
                # Check if second cell contains a name (usually has more than 10 chars and letters)
                name_cell = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                if len(name_cell) > 10 and any(c.isalpha() for c in name_cell):
                    student_row = row
                    break

        if not student_row:
            return []

        value_cells = student_row.find_all('td')

        # Now map headers to values
        current_cell_idx = 0
        ignore_names = ['', 'Matrícula', 'Nome', 'Sit.', 'Faltas', 'Resultado', 'Situação']

        for i, header in enumerate(main_headers):
            header_text = header.get_text(strip=True)
            colspan = int(header.get('colspan') or 1)

            # Skip columns we don't care about
            if header_text in ignore_names:
                current_cell_idx += colspan
                continue

            # This is a grade column
            group_name = header_text

            if colspan == 1:
                # Single value (no sub-grades)
                if current_cell_idx < len(value_cells):
                    val_text = value_cells[current_cell_idx].get_text(strip=True)
                    val = self._parse_float(val_text)

                    if val is not None or val_text not in ['', '-', '--', 'S/N']:
                        grades.append({
                            'name': group_name,
                            'value': val,
                            'type': 'single'
                        })
                current_cell_idx += 1
            else:
                # Multiple sub-grades
                sub_grades = []

                # Extract ALL sub-grades for this group (including empty ones)
                # This ensures proper alignment and prevents skipping columns
                for j in range(colspan):
                    cell_idx = current_cell_idx + j

                    if cell_idx >= len(value_cells):
                        break

                    val_text = value_cells[cell_idx].get_text(strip=True)
                    val = self._parse_float(val_text)

                    # Find the corresponding sub-header
                    # The mapping is direct: cell_idx corresponds to sub-header with index=cell_idx
                    sub_name = "Nota"

                    for sh in sub_headers_clean:
                        if sh['index'] == cell_idx:
                            sub_name = sh['text']

                            # Try to get descriptive name from hidden input
                            sub_id = sh['id']
                            if sub_id and sub_id.startswith('aval_'):
                                grade_id = sub_id[5:]
                                name_input = page.soup.find('input', id=f'denAval_{grade_id}')
                                if name_input and name_input.get('value'):
                                    sub_name = name_input.get('value')
                            break

                    # Add ALL grades to maintain structure
                    # Only skip completely empty cells (no text at all)
                    if val_text:  # Has some text (even if it's "-" or "S/N")
                        sub_grades.append({
                            'name': sub_name,
                            'value': val
                        })

                if sub_grades:
                    grades.append({
                        'name': group_name,
                        'type': 'group',
                        'grades': sub_grades
                    })

                current_cell_idx += colspan

        return grades

    def _parse_float(self, text):
        """
        Parse a string to float, handling Brazilian decimal format.
        Returns None if parsing fails or text is empty/dash.
        """
        if not text or text in ['-', '--', 'S/N', '']:
            return None

        text = text.strip()

        try:
            return float(text.replace(',', '.'))
        except ValueError:
            return None