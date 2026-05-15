"""
Generate all 5 UML diagrams for Student Performance Prediction project.
Saves to static/charts/
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

BASE   = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(BASE, "static", "charts")
os.makedirs(OUTDIR, exist_ok=True)

N="#FFFFFF"; C="#2563EB"; PU="#9333EA"; G="#16A34A"
CO="#DC2626"; GO="#CA8A04"; W="#0F172A"; LG="#475569"; CA="#F1F5F9"

def sv(fig, nm):
    fig.savefig(os.path.join(OUTDIR,nm),dpi=150,bbox_inches="tight",facecolor=N)
    plt.close(fig); print("Saved:",nm)

def aro(ax,x1,y1,x2,y2,col=LG,lbl="",ret=False):
    sty="<-" if ret else "->"
    ax.annotate("",xy=(x2,y2),xytext=(x1,y1),
        arrowprops=dict(arrowstyle=sty,color=col,lw=1.3,mutation_scale=12))
    if lbl: ax.text((x1+x2)/2,(y1+y2)/2+0.1,lbl,ha="center",color=GO,fontsize=7.5)

def ln(ax,x1,y1,x2,y2,col=LG): ax.plot([x1,x2],[y1,y2],color=col,lw=1.2)

# ── 1. USE CASE ──────────────────────────────────────
fig,ax=plt.subplots(figsize=(12,7)); fig.patch.set_facecolor(N)
ax.set_facecolor(N); ax.set_xlim(0,12); ax.set_ylim(0,7); ax.axis("off")
ax.set_title("Use Case Diagram",color=W,fontsize=13,fontweight="bold")
ax.add_patch(FancyBboxPatch((2.5,0.3),6.5,6.2,boxstyle="round,pad=0.15",
    edgecolor=C,facecolor=CA,lw=2))
ax.text(5.75,6.25,"Student Performance Prediction System",
    ha="center",color=C,fontsize=9,fontweight="bold")
def act(ax,x,y,lb,col):
    ax.add_patch(plt.Circle((x,y+0.5),0.2,color=col,zorder=4))
    ax.plot([x,x],[y,y+0.3],color=col,lw=2)
    ax.plot([x-0.25,x+0.25],[y+0.15,y+0.15],color=col,lw=2)
    ax.plot([x,x-0.2],[y,y-0.25],color=col,lw=2)
    ax.plot([x,x+0.2],[y,y-0.25],color=col,lw=2)
    ax.text(x,y-0.45,lb,ha="center",color=col,fontsize=8,fontweight="bold")
act(ax,1.2,4.0,"Teacher/\nAdmin",C); act(ax,1.2,1.5,"Student",G)
act(ax,11.1,3.0,"ML System",GO)
ucs=[("Upload CSV / Excel",5.75,5.5,C),("Manual Entry",5.75,4.6,PU),
     ("View Predictions",5.75,3.7,CO),("Download Report",5.75,2.8,G),
     ("View Charts",5.75,1.9,C),("View SHAP",5.75,1.0,GO)]
for lb,ux,uy,uc in ucs:
    ax.add_patch(mpatches.Ellipse((ux,uy),3.3,0.55,edgecolor=uc,facecolor=N,lw=1.5))
    ax.text(ux,uy,lb,ha="center",va="center",color="#000000",fontsize=8)
for _,ux,uy,_ in ucs: ln(ax,1.8,4.2,ux-1.65,uy)
for _,ux,uy,_ in [ucs[2],ucs[3],ucs[5]]: ln(ax,10.6,3.0,ux+1.65,uy)
sv(fig,"uml_use_case.png")

# ── 2. CLASS DIAGRAM ──────────────────────────────────
fig,ax=plt.subplots(figsize=(14,8)); fig.patch.set_facecolor(N)
ax.set_facecolor(N); ax.set_xlim(0,14); ax.set_ylim(0,8); ax.axis("off")
ax.set_title("Class Diagram",color=W,fontsize=13,fontweight="bold")
def cls(ax,x,y,w,title,attrs,methods,tc=C):
    RH=0.36; TH=0.48; ah=len(attrs)*RH; mh=len(methods)*RH
    ax.add_patch(FancyBboxPatch((x,y+ah+mh),w,TH,boxstyle="square,pad=0",fc=tc,ec=W,lw=1.5))
    ax.text(x+w/2,y+ah+mh+TH/2,title,ha="center",va="center",color="#FFFFFF",fontsize=9,fontweight="bold")
    ax.add_patch(FancyBboxPatch((x,y+mh),w,ah,boxstyle="square,pad=0",fc=CA,ec=W,lw=1))
    for i,a in enumerate(attrs):
        cc=GO if a.startswith("+PK") or a.startswith("+FK") else LG
        ax.text(x+0.1,y+mh+ah-(i+0.5)*RH,a,va="center",color=cc,fontsize=7)
    ax.add_patch(FancyBboxPatch((x,y),w,mh,boxstyle="square,pad=0",fc=CA,ec=W,lw=1))
    ax.plot([x,x+w],[y+mh,y+mh],color=LG,lw=0.8)
    for i,m in enumerate(methods):
        ax.text(x+0.1,y+mh-(i+0.5)*RH,m,va="center",color=G,fontsize=7)
cls(ax,0.2,4.2,3.0,"FlaskApp",
    ["+ host: str","+ port: int","+ model: Pipeline"],
    ["+ index()","+ predict()","+ download()","+ manual_predict()"],C)
cls(ax,3.8,5.0,3.2,"MLPipeline",
    ["+ preprocessor: ColumnTransformer","+ best_model: classifier","+ cv_scores: dict"],
    ["+ train(X,y)","+ select_best()","+ predict(X)","+ get_metrics()"],PU)
cls(ax,7.8,5.2,2.8,"StudentData",
    ["+ school","+ age","+ studytime","+ absences","+ failures","+ passed"],
    ["+ load_csv(path)","+ preprocess()","+ validate()"],G)
cls(ax,3.8,1.2,3.2,"ChartGenerator",
    ["+ output_dir: str","+ df: DataFrame"],
    ["+ plot_counts()","+ plot_heatmap()","+ plot_shap()","+ plot_confusion()","+ plot_feat_imp()"],CO)
cls(ax,7.8,1.0,2.8,"ReportExporter",
    ["+ filename: str","+ metrics: dict"],
    ["+ to_csv()","+ to_pdf()","+ generate_tips()"],GO)
cls(ax,11.0,4.0,2.6,"SHAPExplainer",
    ["+ model","+ X: DataFrame","+ shap_values"],
    ["+ explain()","+ plot_summary()","+ get_top_features()"],C)
aro(ax,3.2,5.5,3.8,5.8); aro(ax,3.2,5.0,3.8,5.3)
aro(ax,7.0,5.8,7.8,5.8); aro(ax,7.0,5.3,7.8,5.3)
aro(ax,5.4,5.0,5.4,3.6); aro(ax,7.0,2.5,7.8,2.5)
aro(ax,10.5,5.5,11.0,5.0)
sv(fig,"uml_class.png")

# ── 3. SEQUENCE DIAGRAM ──────────────────────────────
fig,ax=plt.subplots(figsize=(13,8)); fig.patch.set_facecolor(N)
ax.set_facecolor(N); ax.set_xlim(0,13); ax.set_ylim(0,8); ax.axis("off")
ax.set_title("Sequence Diagram – Bulk CSV Prediction",color=W,fontsize=13,fontweight="bold")
actors_s=[(1.0,"User",C),(3.5,"Flask",PU),(6.0,"MLPipeline",G),(8.5,"Charts",CO),(11.0,"Exporter",GO)]
for ax_x,lb,col in actors_s:
    ax.add_patch(FancyBboxPatch((ax_x-0.5,7.1),1.0,0.55,boxstyle="round,pad=0.05",fc=col,ec=W,lw=1.5))
    ax.text(ax_x,7.37,lb,ha="center",va="center",color=N,fontsize=8,fontweight="bold")
    ax.plot([ax_x,ax_x],[0.3,7.1],color=col,lw=1,alpha=0.4)
msgs_s=[
    (1.0,3.5,6.6,"1. POST /predict (CSV)",W,False),
    (3.5,6.0,5.9,"2. preprocess(df)",W,False),
    (6.0,3.5,5.2,"3. predictions[ ]",GO,True),
    (3.5,8.5,4.5,"4. generate_charts()",W,False),
    (8.5,3.5,3.8,"5. chart_paths[ ]",GO,True),
    (3.5,11.0,3.1,"6. to_csv(results)",W,False),
    (11.0,3.5,2.4,"7. download_url",GO,True),
    (3.5,6.0,1.7,"8. shap_explain()",W,False),
    (6.0,3.5,1.0,"9. shap_values + plot",GO,True),
]
for x1,x2,y,lb,col,ret in msgs_s:
    aro(ax,x1,y,x2,y,col,lb,ret)
    ax.add_patch(FancyBboxPatch((x2-0.12,y-0.25),0.24,0.28,
        boxstyle="square,pad=0",fc=PU,ec=W,lw=0.8))
sv(fig,"uml_sequence.png")

# ── 4. DFD ───────────────────────────────────────────
fig,ax=plt.subplots(figsize=(13,7)); fig.patch.set_facecolor(N)
ax.set_facecolor(N); ax.set_xlim(0,13); ax.set_ylim(0,7); ax.axis("off")
ax.set_title("Data Flow Diagram (DFD Level 1)",color=W,fontsize=13,fontweight="bold")
def ext(ax,x,y,w,h,lb,col=C):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.1",fc=col,ec=W,lw=1.5))
    ax.text(x+w/2,y+h/2,lb,ha="center",va="center",color=N,fontsize=8,fontweight="bold")
def prc(ax,x,y,r,lb,col=PU):
    ax.add_patch(plt.Circle((x,y),r,fc=col,ec=W,lw=1.5,zorder=3))
    ax.text(x,y,lb,ha="center",va="center",color=W,fontsize=7.5,fontweight="bold")
def sto(ax,x,y,w,lb):
    ax.plot([x,x+w],[y,y],color=LG,lw=1.5); ax.plot([x,x+w],[y-0.35,y-0.35],color=LG,lw=1.5)
    ax.plot([x,x],[y,y-0.35],color=LG,lw=1.5)
    ax.text(x+w/2,y-0.18,lb,ha="center",va="center",color=W,fontsize=8)
ext(ax,0.1,5.8,1.8,0.6,"Teacher/Admin",C); ext(ax,0.1,0.4,1.8,0.6,"Student",G)
ext(ax,10.9,3.1,1.8,0.6,"ML Model\n(model.pkl)",GO)
prc(ax,3.5,5.8,0.75,"1.0\nUpload\nValidate",C); prc(ax,6.5,5.8,0.75,"2.0\nPreprocess",PU)
prc(ax,6.5,3.5,0.75,"3.0\nPredict",PU); prc(ax,3.5,3.5,0.75,"4.0\nCharts",CO)
prc(ax,5.0,1.5,0.75,"5.0\nExport",G)
sto(ax,4.5,6.8,3.5,"D1: Student Dataset"); sto(ax,4.5,2.65,3.5,"D2: Predictions")
sto(ax,4.5,0.85,3.5,"D3: Charts & Reports")
aro(ax,1.9,6.1,2.75,5.8,W,"Upload"); aro(ax,4.25,5.8,5.75,5.8,W,"Validated")
aro(ax,7.25,5.8,7.25,4.25,W,"Features"); aro(ax,7.25,3.5,10.9,3.4,W,"Matrix")
aro(ax,10.9,3.3,7.25,3.1,GO,"Predictions"); aro(ax,6.5,2.75,6.5,2.6)
aro(ax,5.75,3.5,4.25,3.5,W,"Results"); aro(ax,3.5,2.75,3.5,2.6)
aro(ax,4.3,1.5,4.5,0.9); aro(ax,3.5,1.5,1.9,0.8,GO,"View")
sv(fig,"uml_dfd.png")

# ── 5. ER DIAGRAM ────────────────────────────────────
fig,ax=plt.subplots(figsize=(14,7)); fig.patch.set_facecolor(N)
ax.set_facecolor(N); ax.set_xlim(0,14); ax.set_ylim(0,7); ax.axis("off")
ax.set_title("ER Diagram",color=W,fontsize=13,fontweight="bold")
def ent(ax,x,y,w,name,attrs,col=C):
    RH=0.34; TH=0.45; ah=len(attrs)*RH
    ax.add_patch(FancyBboxPatch((x,y),w,TH,boxstyle="square,pad=0",fc=col,ec=W,lw=1.5))
    ax.text(x+w/2,y+TH/2,name,ha="center",va="center",color=N,fontsize=9,fontweight="bold")
    ax.add_patch(FancyBboxPatch((x,y-ah),w,ah,boxstyle="square,pad=0",fc=CA,ec=W,lw=1))
    for i,a in enumerate(attrs):
        cc=GO if a.startswith("PK") or a.startswith("FK") else LG
        ax.text(x+0.1,y-ah+(len(attrs)-i-0.55)*RH,a,va="center",color=cc,fontsize=7.5)
ent(ax,0.2,6.2,3.5,"STUDENT",
    ["PK  student_id","    school","    sex","    age",
     "    studytime","    failures","    absences","    passed"],C)
ent(ax,4.5,6.2,3.5,"PREDICTION",
    ["PK  prediction_id","FK  student_id","    model_used",
     "    result","    probability","    timestamp"],PU)
ent(ax,8.8,6.2,3.5,"ML_MODEL",
    ["PK  model_id","    model_name","    cv_accuracy",
     "    precision","    recall","    f1_score","    is_best"],G)
ent(ax,0.2,2.0,3.5,"STUDENT_SOCIAL",
    ["PK  social_id","FK  student_id","    goout",
     "    Dalc","    Walc","    health","    romantic"],CO)
ent(ax,4.5,2.0,3.5,"REPORT",
    ["PK  report_id","FK  prediction_id","    file_path",
     "    generated_at","    format"],GO)
def rel(ax,x,y,lb,col=LG):
    ax.add_patch(mpatches.Ellipse((x,y),1.4,0.38,fc=CA,ec=col,lw=1.5))
    ax.text(x,y,lb,ha="center",va="center",color=col,fontsize=8)
rel(ax,4.0,5.9,"makes"); rel(ax,8.1,5.9,"uses")
rel(ax,1.9,3.3,"has"); rel(ax,6.2,3.3,"generates")
ln(ax,3.7,5.9,3.4,5.9); ln(ax,4.6,5.9,4.4,5.9)
ln(ax,8.3,5.9,8.1,5.9); ln(ax,8.8,5.9,8.8,5.9)
ln(ax,1.9,5.4,1.9,3.5); ln(ax,1.9,3.1,1.9,2.45)
ln(ax,6.2,5.4,6.2,3.5); ln(ax,6.2,3.1,6.2,2.45)
sv(fig,"uml_er.png")

print("\nAll 5 diagrams generated successfully!")
