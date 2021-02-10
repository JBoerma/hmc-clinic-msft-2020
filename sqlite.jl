### A Pluto.jl notebook ###
# v0.12.20

using Markdown
using InteractiveUtils

# ╔═╡ 1181e056-277c-11eb-2823-9bc6bfab91ea
begin
	using DataFrames
	using DataFramesMeta
	using CSVFiles
	using Plots
	using StatsPlots
	using Statistics
	using Distributions
	using StatsBase
	using EmpiricalCDFs
	using SQLite
	db = SQLite.DB("~/Documents/clinic/hmc-clinic-msft-2020/results/results.db")
	gr()
end

# ╔═╡ 5cc20840-277a-11eb-2770-3551050cc439
begin
	import Pkg;
	Pkg.add("CSVFiles");
	Pkg.add("DataFrames");
	Pkg.add("DataFramesMeta");
	Pkg.add("Plots");
	Pkg.add("StatsPlots");
	Pkg.add("Distributions");
	Pkg.add("StatsBase");
	Pkg.add("EmpiricalCDFs");
end

# ╔═╡ d132ad42-277a-11eb-1310-ff6638b8cdbe
begin
	chromium = DBInterface.execute(db, "SELECT * FROM timings WHERE browser='chromium' AND server!='Error'") |> DataFrame;
	chromium.connectTime = chromium.connectEnd .- chromium.connectStart;
	chromium.secureConnectTime = chromium.connectEnd .- chromium.secureConnectionStart;
	chromium.requestToResponse = chromium.responseStart .- chromium.requestStart;
	chromium.responseTime = chromium.responseEnd .- chromium.responseStart;
	chromium = chromium[:, [:httpVersion, :server, :connectTime, :secureConnectTime, :requestToResponse, :responseTime]]
	replace!(chromium.server, "nginx/1.16.1" => "Quiche");
	replace!(chromium.server, "nginx/1.19.6" => "NGINX");
	chromium;
end

# ╔═╡ 70803d6e-277c-11eb-1f54-f91572fc8a82
begin
	firefox = DBInterface.execute(db, "SELECT * FROM timings WHERE browser='firefox' AND server!='Error'") |> DataFrame;
	firefox.connectTime = firefox.connectEnd .- firefox.connectStart;
	firefox.secureConnectTime = firefox.connectEnd .- firefox.secureConnectionStart;
	firefox.requestToResponse = firefox.responseStart .- firefox.requestStart;
	firefox.responseTime = firefox.responseEnd .- firefox.responseStart;
	firefox = firefox[:, [:httpVersion, :server, :connectTime, :secureConnectTime, :requestToResponse, :responseTime]]
	replace!(firefox.server, "nginx/1.16.1" => "Quiche");
	replace!(firefox.server, "nginx/1.19.6" => "NGINX");
	firefox;
end

# ╔═╡ 91022abe-27c9-11eb-3718-9db474186dd3
begin
	edge = DBInterface.execute(db, "SELECT * FROM timings WHERE browser='edge' AND server!='Error'") |> DataFrame;
	edge.connectTime = edge.connectEnd .- edge.connectStart;
	edge.secureConnectTime = edge.connectEnd .- edge.secureConnectionStart;
	edge.requestToResponse = edge.responseStart .- edge.requestStart;
	edge.responseTime = edge.responseEnd .- edge.responseStart;
	edge = edge[:, [:httpVersion, :server, :connectTime, :secureConnectTime, :requestToResponse, :responseTime]]
	replace!(edge.server, "nginx/1.16.1" => "Quiche");
	replace!(edge.server, "nginx/1.19.6" => "NGINX");
	edge;
end

# ╔═╡ 7ffc3f0a-2785-11eb-2562-651f2f1fad6d
plotly()

# ╔═╡ 1410578a-2786-11eb-0939-b53366b9e593
begin
	@df chromium violin(string.(:httpVersion, ":", :server), :connectTime, linewidth=0, label="")
	@df chromium boxplot!(string.(:httpVersion, ":", :server), :connectTime, fillalpha=0.75, linewidth=2, label="", ylabel="Time (MS)", title="Chromium: Connect Time")
end

# ╔═╡ 96cb1522-27d4-11eb-0477-938e8b1e3da7
begin
	@df chromium bar(group = (:httpVersion, :server), ecdf(:connectTime), title = "Chromium H2 Vs. H3 Connect Time CDF", xlabel="Time (ms)", legend=:right, ylabel="Percentile");
end

# ╔═╡ b5d5d570-27c9-11eb-2354-d7154669c6ec
begin
	@df edge violin(string.(:httpVersion, ":", :server), :connectTime, linewidth=0, label="")
	@df edge boxplot!(string.(:httpVersion, ":", :server), :connectTime, fillalpha=0.75, linewidth=2, label="", ylabel="Time (MS)", title="Edge: Connect Time")
end

# ╔═╡ 723d7358-27d4-11eb-0974-f5675aedd553
begin
	@df edge bar(group = (:httpVersion, :server), ecdf(:connectTime), title = "Edge H2 Vs. H3 Connect Time CDF", xlabel="Time (ms)", legend=:right, ylabel="Percentile");
end

# ╔═╡ 531a104c-278b-11eb-368b-87f1f89b0af3
begin
	@df firefox violin(string.(:httpVersion, ":", :server), :connectTime, linewidth=0, label="")
	@df firefox boxplot!(string.(:httpVersion, ":", :server), :connectTime, fillalpha=0.75, linewidth=2, label="", ylabel="Time (MS)", title="Firefox: Connect Time")
end

# ╔═╡ 3176baf0-27d4-11eb-1ac6-6f3c42d0b2e0
begin
	@df firefox bar(group = (:httpVersion, :server), ecdf(:connectTime), title = "Firefox H2 Vs. H3 Connect Time CDF", xlabel="Time (ms)", func=:cdf, legend=:topleft, ylabel="Percentile");
end

# ╔═╡ 83f81704-278b-11eb-2134-ab2da245968b
begin
	@df chromium violin(string.(:httpVersion, ":", :server), :requestToResponse, linewidth=0, label="")
	@df chromium boxplot!(string.(:httpVersion, ":", :server), :requestToResponse, fillalpha=0.75, linewidth=2, label="", ylabel="Time (MS)", title="Chromium: Request End to Response Start")
end

# ╔═╡ 0ad4624e-27d4-11eb-321b-b1f11eb2b9d2
begin
	@df chromium bar(ecdf(@where(chromium, :httpVersion .== "h2").requestToResponse), title = "Chromium H2 Vs. H3 Request End to Response Start CDF", label="H2");
	@df chromium bar!(ecdf(@where(chromium, :httpVersion .== "h3").requestToResponse), label="H3", legend=:right);
end

# ╔═╡ d187c9ea-27c9-11eb-315e-93304819a8d0
begin
	@df edge violin(string.(:httpVersion, ":", :server), :requestToResponse, linewidth=0, label="")
	@df edge boxplot!(string.(:httpVersion, ":", :server), :requestToResponse, fillalpha=0.75, linewidth=2, label="", ylabel="Time (MS)", title="Edge: Time from Request to Response")
end

# ╔═╡ f3ba2902-27d3-11eb-108b-1dec44dae7c5
begin
	@df edge plot(group = (:httpVersion, :server), ecdf(:requestToResponse), title = "Edge H2 Vs. H3 Connect Time CDF", xlabel="Time (ms)", legend=:right, ylabel="Percentile");
end

# ╔═╡ d5864ea6-278b-11eb-21df-236c75f42bef
begin
	@df firefox violin(string.(:httpVersion, ":", :server), :requestToResponse, linewidth=0, label="");
	@df firefox boxplot!(string.(:httpVersion, ":", :server), :requestToResponse, fillalpha=0.75, linewidth=2, ylabel="Time (MS)", title="Firefox: Time from Request to Response", label="");
end

# ╔═╡ b20f9d40-27d3-11eb-0561-ab49d0c559c1
begin
	@df firefox bar(group = (:httpVersion, :server), ecdf(:requestToResponse), title = "Firefox H2 Vs. H3 Time from Request to Response CDF", xlabel="Time (ms)", legend=:right, ylabel="Percentile");
end

# ╔═╡ 2bda19ca-27ca-11eb-025b-2901409532c1
begin
	@df chromium violin(string.(:httpVersion, ":", :server), :responseTime, linewidth=0, label="")
	@df chromium boxplot!(string.(:httpVersion, ":", :server), :responseTime, fillalpha=0.75, linewidth=2, label="", ylabel="Time (MS)", title="Chromium: Response Times")
end

# ╔═╡ e285bcde-27ce-11eb-0f5b-8b1ce3b8f7ca
begin
	@df chromium bar(group = (:httpVersion, :server), ecdf(:responseTime), title = "Chromium H2 Vs. H3 Response Time CDF", xlabel="Time (ms)", legend=:right, ylabel="Percentile");
end

# ╔═╡ 6a88c2a2-27ca-11eb-1dfc-c37db4c0edd0
begin
	@df edge violin(string.(:httpVersion, ":", :server), :responseTime, linewidth=0, label="")
	@df edge boxplot!(string.(:httpVersion, ":", :server), :responseTime, fillalpha=0.75, linewidth=2, label="", ylabel="Time (MS)", title="Edge: Response Times")
end

# ╔═╡ 58b938fa-27d3-11eb-35e4-df3947096b53
begin
	@df edge bar(group = (:httpVersion, :server), ecdf(:responseTime), title = "Edge H2 Vs. H3 Response Time CDF", xlabel="Time (ms)", legend=:right, ylabel="Percentile");
end

# ╔═╡ 62204754-27ca-11eb-2a6e-a565700d70f2
begin
	@df firefox violin(string.(:httpVersion, ":", :server), :responseTime, linewidth=0, label="")
	@df firefox boxplot!(string.(:httpVersion, ":", :server), :responseTime, fillalpha=0.75, linewidth=2, label="", ylabel="Time (MS)", title="Firefox: Response Times")
end

# ╔═╡ 88ebf58a-27d3-11eb-17d4-9f06aa29a398
begin
	@df firefox bar(group = (:httpVersion, :server), ecdf(:responseTime), title = "Firefox H2 Vs. H3 Response Time CDF", xlabel="Time (ms)", legend=:right, ylabel="Percentile");
end

# ╔═╡ cc86402e-27ca-11eb-38d0-4b936dc62c0c
combined = vcat(chromium, firefox, edge);

# ╔═╡ c9a17cce-27cb-11eb-3bf7-c1f07888e4f5
begin
	@df combined violin(string.(:httpVersion, ":", :server), :connectTime, linewidth=0, label="")
	@df combined boxplot!(string.(:httpVersion, ":", :server), :connectTime, fillalpha=0.75, linewidth=2, label="", ylabel="Time (MS)", title="Overall: Connect Time")
end

# ╔═╡ 0e5df8fe-27d8-11eb-2b6a-ebc6b8ae4800
begin
	@df combined bar(group = (:httpVersion, :server), ecdf(:responseTime), title = "Overall H2 Vs. H3 Response Time CDF", xlabel="Time (ms)", legend=:right, ylabel="Percentile");
end

# ╔═╡ 0a909e2c-27cc-11eb-2512-5bc30f89ef55
begin
	@df combined violin(string.(:httpVersion, ":", :server), :requestToResponse, linewidth=0, label="")
	@df combined boxplot!(string.(:httpVersion, ":", :server), :requestToResponse, fillalpha=0.75, linewidth=2, label="", ylabel="Time (MS)", title="Overall: Response Time")
end

# ╔═╡ 370f50ba-27d8-11eb-3d00-bf2fd1cbb6ab
begin
	@df combined bar(group = (:httpVersion, :server), ecdf(:requestToResponse), title = "Overall H2 Vs. H3 Time From Request Start to Response Start CDF", xlabel="Time (ms)", legend=:right, ylabel="Percentile");
end

# ╔═╡ bab1b2f6-27cb-11eb-1e2c-59f4d7f62db3
begin
	@df combined violin(string.(:httpVersion, ":", :server), :responseTime, linewidth=0, label="")
	@df combined boxplot!(string.(:httpVersion, ":", :server), :responseTime, fillalpha=0.75, linewidth=2, label="", ylabel="Time (MS)", title="Overall: Response Times")
end

# ╔═╡ 5e1cdaa4-27d8-11eb-3255-93bab34fcb00
begin
	@df combined bar(group = (:httpVersion, :server), ecdf(:responseTime), title = "Overall H2 Vs. H3 Response Time CDF", xlabel="Time (ms)", legend=:right, ylabel="Percentile");
end

# ╔═╡ Cell order:
# ╟─5cc20840-277a-11eb-2770-3551050cc439
# ╠═1181e056-277c-11eb-2823-9bc6bfab91ea
# ╠═d132ad42-277a-11eb-1310-ff6638b8cdbe
# ╠═70803d6e-277c-11eb-1f54-f91572fc8a82
# ╠═91022abe-27c9-11eb-3718-9db474186dd3
# ╟─7ffc3f0a-2785-11eb-2562-651f2f1fad6d
# ╠═1410578a-2786-11eb-0939-b53366b9e593
# ╟─96cb1522-27d4-11eb-0477-938e8b1e3da7
# ╠═b5d5d570-27c9-11eb-2354-d7154669c6ec
# ╟─723d7358-27d4-11eb-0974-f5675aedd553
# ╟─531a104c-278b-11eb-368b-87f1f89b0af3
# ╟─3176baf0-27d4-11eb-1ac6-6f3c42d0b2e0
# ╟─83f81704-278b-11eb-2134-ab2da245968b
# ╟─0ad4624e-27d4-11eb-321b-b1f11eb2b9d2
# ╟─d187c9ea-27c9-11eb-315e-93304819a8d0
# ╟─f3ba2902-27d3-11eb-108b-1dec44dae7c5
# ╟─d5864ea6-278b-11eb-21df-236c75f42bef
# ╟─b20f9d40-27d3-11eb-0561-ab49d0c559c1
# ╟─2bda19ca-27ca-11eb-025b-2901409532c1
# ╟─e285bcde-27ce-11eb-0f5b-8b1ce3b8f7ca
# ╟─6a88c2a2-27ca-11eb-1dfc-c37db4c0edd0
# ╟─58b938fa-27d3-11eb-35e4-df3947096b53
# ╟─62204754-27ca-11eb-2a6e-a565700d70f2
# ╠═88ebf58a-27d3-11eb-17d4-9f06aa29a398
# ╟─cc86402e-27ca-11eb-38d0-4b936dc62c0c
# ╠═c9a17cce-27cb-11eb-3bf7-c1f07888e4f5
# ╟─0e5df8fe-27d8-11eb-2b6a-ebc6b8ae4800
# ╟─0a909e2c-27cc-11eb-2512-5bc30f89ef55
# ╟─370f50ba-27d8-11eb-3d00-bf2fd1cbb6ab
# ╟─bab1b2f6-27cb-11eb-1e2c-59f4d7f62db3
# ╟─5e1cdaa4-27d8-11eb-3255-93bab34fcb00
