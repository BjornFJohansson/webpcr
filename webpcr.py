#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""docstring."""

import datetime

from textwrap import dedent

from flask import Flask
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for

from wtforms.fields import SelectField
from wtforms.fields import DecimalField
from wtforms.fields import TextAreaField
from wtforms.fields import SubmitField

from Bio.SeqUtils import MeltingTemp as _mt

from pydna import __version__ as version
from pydna.parsers import parse
from pydna.amplify import Anneal
from pydna.design import primer_design


# https://blog.pythonanywhere.com/121
# export FLASK_APP=webpcr.py&&export FLASK_ENV=development&&flask run
# https://pypi.org/project/Bootstrap-Flask

# https://elc.github.io/posts/executable-flask-pyinstaller
# https://stackoverflow.com/questions/32149892/flask-application-built-using-pyinstaller-not-rendering-index-html

# pyinstaller -w -F --add-data "templates:templates"
# --add-data "static:static" webpcr_app.py






from pydna.tm import tm_default

from flask_wtf import FlaskForm

nn_tableoptions = [(1, "DNA_NN1 - Breslauer et al. (1986), "
                       "Proc Natl Acad Sci USA 83: 3746-3750"),
                   (2, "DNA_NN2 - Sugimoto et al. (1996),"
                       " Nuc Acids Res 24 : 4501-4505"),
                   (3, "DNA_NN3 - Allawi and SantaLucia (1997),"
                       " Biochemistry 36: 10581-10594"),
                   (4, "DNA_NN4 - SantaLucia & Hicks (2004),"
                       " Annu. Rev. Biophys. Biomol. Struct 33: 415-440")]


saltoptions = [(1, "1. 16.6 x log[Na+] (Schildkraut & Lifson"
                   " (1965), Biopolymers 3: 195-208)"),
               (2, "2. 16.6 x log([Na+]/(1.0 + 0.7*[Na+])) (Wetmur"
                   " (1991), Crit Rev Biochem Mol Biol 126: 227-259)"),
               (3, "3. 12.5 x log(Na+] (SantaLucia et al. (1996),"
                   " Biochemistry 35: 3555-3562"),
               (4, "4. 11.7 x log[Na+] (SantaLucia (1998),"
                   " Proc Natl Acad Sci USA 95: 1460-1465"),
               (5, "5. Correction for deltaS: 0.368 x (N-1) x ln[Na+] (Santa"
                   "Lucia (1998), Proc Natl Acad Sci USA 95: 1460-1465)"),
               (6, "6. (4.29(%GC)-3.95)x1e-5 x ln[Na+] + 9.40e-6 x ln[Na+]^2"
                   " (Owczarzy et al. (2004), Biochemistry 43: 3537-3554)"),
               (7, "7. Complex formula with decision tree and"
                   " 7 empirical constants.")]


class CustomForm(FlaskForm):
    """docstring."""

    table = SelectField('nn_table',
                        choices=nn_tableoptions,
                        default=4)
    salt = SelectField('saltcorr',
                       choices=saltoptions,
                       default=7)
    Na = DecimalField("Na", default=40)
    Mg = DecimalField("Mg", default=1.5)
    dnac1 = DecimalField("dnac1", default=250)
    dnac2 = DecimalField("dnac2", default=250)

    K = DecimalField("K", default=0)
    Tris = DecimalField("Tris", default=75.0)
    dNTPs = DecimalField("dNTPs", default=0.8)

    primer_text = TextAreaField('primer_text',
                                default=">MyPrimer\nATGGCAGTTGAGAAGA")
    send = SubmitField('calculate')
    clear = SubmitField('clear')


nn_tables = {"1": _mt.DNA_NN1,
             "2": _mt.DNA_NN2,
             "3": _mt.DNA_NN3,
             "4": _mt.DNA_NN4}

app = Flask(__name__)

app.config.update(dict(
    SECRET_KEY="powerful_secretkey",
    WTF_CSRF_SECRET_KEY="a_csrf_secret_key"))

results = []
comments = []
design_results = []

separator = '-'*80


@app.route("/", methods=["GET", "POST"])
def index():
    """docstring."""
    return render_template("index.html",
                           version=version)


@app.route("/tm", methods=["GET", "POST"])
def tm():
    """docstring."""
    form = CustomForm()
    if request.method == "GET":
        return render_template("tm.html",
                               form=form,
                               comments=comments)

    if 'clear' in request.form:
        comments.clear()
        return redirect(url_for('tm'))

    user_data = request.form

    primers = parse(user_data['primer_text'])

    for primer in primers:
        tm = tm_default(primer.seq,
                        check=True,
                        strict=True,
                        c_seq=None,
                        shift=0,
                        nn_table=nn_tables[user_data['table']],
                        tmm_table=None,
                        imm_table=None,
                        de_table=None,
                        dnac1=float(user_data['dnac1']),
                        dnac2=float(user_data['dnac2']),
                        selfcomp=False,
                        Na=float(user_data['Na']),
                        K=float(user_data['K']),
                        Tris=float(user_data['Tris']),
                        Mg=float(user_data['Mg']),
                        dNTPs=float(user_data['dNTPs']),
                        saltcorr=int(user_data['salt']))
        primer.description = f"tm={round(tm, 3)}"
        comments.append(primer.format("fasta"))
    return redirect(url_for('tm'))
    # return render_template("tm.html",
    #                        form=form,
    #                        comments=comments)




@app.route("/pcr", methods=["GET", "POST"])
def pcr():
    """docstring."""
    if request.method == "GET":
        return render_template("pcr.html",
                               results=results,
                               version=version)

    if 'clear' in request.form:
        results.clear()
        return redirect(url_for('pcr'))

    user_data = request.form["contents"]

    sequences = parse(user_data)

    template = sequences.pop()

    primer_sequences = sequences

    homology_limit = 12
    cutoff_detailed_figure = 6
    cutoff_detailed_figure = 5

    ann = Anneal(primer_sequences,
                 template,
                 limit=homology_limit)

    products = ann.products
    number_of_products = len(products)
    now = datetime. datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    result_text = (f'pydna {version} UTC {now} '
                   f'Number of products formed: {number_of_products}\n')

    if number_of_products == 0:
        result_text += ann.report().strip()

    elif 1 <= number_of_products <= cutoff_detailed_figure:
        result_text += (f'{ann.report()}\n'
                        f'{separator}')
        for amplicon in products:
            result_text += dedent(f'''
            >{amplicon.forward_primer.name} {len(amplicon.forward_primer)}-mer
            {amplicon.forward_primer.seq}
            >{amplicon.reverse_primer.name} {len(amplicon.reverse_primer)}-mer
            {amplicon.reverse_primer.seq}
            >{ann.template.name}
            {ann.template.seq}
            ----
            {{}}
            ----
            >{amplicon.name}
            {amplicon.seq}
            ----
            Taq DNA polymerase
            {{}}
            Pfu-Sso7d DNA polymerase
            {{}}''')
            result_text = result_text.format(amplicon.figure(),
                                             amplicon.program(),
                                             amplicon.dbd_program())

    results.append(result_text)

    return redirect(url_for('pcr'))


@app.route("/primerdesign", methods=["GET", "POST"])
def primerdesign():
    if request.method == "GET":
        return render_template("primerdesign.html",
                               results=design_results,
                               version=version)
    if 'clear' in request.form:
        design_results.clear()
        return redirect(url_for('primerdesign'))

    user_data = request.form["contents"]

    sequences = parse(user_data)

    template = sequences.pop()

    primer_sequences = sequences

    homology_limit = 12

    amplicon = None

    if primer_sequences:
        p = primer_sequences.pop()
        try:
            amplicon = primer_design(template,
                                     fp=p,
                                     limit=homology_limit)
        except IndexError:  # ValueError
            pass
        try:
            amplicon = primer_design(template,
                                     rp=p,
                                     limit=homology_limit)
        except IndexError:  # ValueError
            result_text = "Primer does not anneal."

    else:
        amplicon = primer_design(template,
                                 limit=homology_limit)

    if amplicon:

        now = datetime. datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        result_text = dedent(f'''
        pydna {version} UTC {now}
        >{amplicon.forward_primer.name} {len(amplicon.forward_primer)}-mer
        {amplicon.forward_primer.seq}
        >{amplicon.reverse_primer.name} {len(amplicon.reverse_primer)}-mer
        {amplicon.reverse_primer.seq}
        >{amplicon.template.name}
        {amplicon.template.seq}
        ----
        {{}}
        ----
        >{amplicon.name}
        {amplicon.seq}
        ----
        Taq DNA polymerase
        {{}}
        Pfu-Sso7d DNA polymerase
        {{}}''')
        result_text = result_text.format(amplicon.figure(),
                                         amplicon.program(),
                                         amplicon.dbd_program())

    design_results.append(result_text)

    return redirect(url_for('primerdesign'))


if __name__ == '__main__':
    from webui import WebUI
    ui = WebUI(app, debug=True)
    ui.run()


# def tm_default(
#     seq,
#     check=True,
#     strict=True,
#     c_seq=None,
#     shift=0,
#     nn_table=_mt.DNA_NN4,  # DNA_NN4: values from SantaLucia & Hicks (2004)
#     tmm_table=None,
#     imm_table=None,
#     de_table=None,
#     dnac1=500 / 2,  # I assume 500 ??M of each primer in the PCR mix
#     dnac2=500 / 2,  # This is what MELTING and Primer3Plus do
#     selfcomp=False,
#     Na=40,
#     K=0,
#     Tris=75.0,  # We use the 10X Taq Buffer with (NH4)2SO4 (above)
#     Mg=1.5,  # 1.5 mM Mg2+ is often seen in modern protocols
#     dNTPs=0.8,  # I assume 200 ??M of each dNTP
#     saltcorr=7,  # Tm = 81.5 + 0.41(%GC) - 600/N + 16.6 x log[Na+]
#     func=_mt.Tm_NN,  # Used by Primer3Plus to calculate the product Tm.
# ):
